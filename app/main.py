from __future__ import annotations

import asyncio
import logging
import stat
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from app.core.bootstrap import ensure_auto_bootstrap_token, log_bootstrap_token
from app.core.clients.http import close_http_client, init_http_client
from app.core.config.settings import get_settings
from app.core.config.settings_cache import get_settings_cache
from app.core.handlers import add_exception_handlers
from app.core.metrics.middleware import MetricsMiddleware
from app.core.metrics.prometheus import MULTIPROCESS_MODE, PROMETHEUS_AVAILABLE, make_scrape_registry, mark_process_dead
from app.core.middleware import (
    add_api_firewall_middleware,
    add_app_version_middleware,
    add_dashboard_auth_proxy_middleware,
    add_request_decompression_middleware,
    add_request_id_middleware,
)
from app.core.middleware.inflight import InFlightMiddleware
from app.core.resilience.backpressure import BackpressureMiddleware
from app.core.resilience.bulkhead import BulkheadMiddleware, get_bulkhead
from app.core.resilience.memory_monitor import configure as configure_memory_monitor
from app.db.session import SessionLocal, close_db, init_background_db, init_db
from app.modules.audit import api as audit_api
from app.modules.dashboard_auth import api as dashboard_auth_api
from app.modules.firecrawl import api as firecrawl_api
from app.modules.firecrawl.refresh import build_firecrawl_refresh_scheduler
from app.modules.firewall import api as firewall_api
from app.modules.health import api as health_api
from app.modules.runtime import api as runtime_api
from app.modules.settings import api as settings_api

logger = logging.getLogger(__name__)


class _MetricsServer(Protocol):
    should_exit: bool

    async def serve(self) -> None: ...


def _resolve_static_asset_path(static_root: Path, requested_path: str) -> Path | None:
    """Return a filesystem path for a SPA asset only when it stays under static_root."""
    normalized = PurePosixPath(requested_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        return None
    full_path, stat_result = StaticFiles(directory=static_root, check_dir=False).lookup_path(normalized.as_posix())
    if stat_result is None or not stat.S_ISREG(stat_result.st_mode):
        return None
    return Path(full_path)


def _is_benign_metrics_bind_failure(exc: BaseException) -> bool:
    if not MULTIPROCESS_MODE:
        return False
    if isinstance(exc, SystemExit):
        return exc.code == 1
    if isinstance(exc, OSError):
        import errno as _errno

        return exc.errno in (_errno.EADDRINUSE, _errno.EADDRNOTAVAIL)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.core.startup as startup_module

    shutdown_state = import_module("app.core.shutdown")
    metrics_server = None
    metrics_server_task: asyncio.Task[None] | None = None

    startup_module._startup_complete = False
    shutdown_state.reset()
    await get_settings_cache().invalidate()
    settings = get_settings()
    if settings.otel_enabled:
        from app.core.tracing.otel import init_tracing

        init_tracing(service_name="firecrawl-lb", endpoint=settings.otel_exporter_endpoint, app=app)
    await init_db()
    init_background_db()
    _auto_bootstrap_token = await ensure_auto_bootstrap_token()
    if _auto_bootstrap_token:
        log_bootstrap_token(logger, _auto_bootstrap_token)
    await init_http_client()
    firecrawl_refresh_scheduler = build_firecrawl_refresh_scheduler(
        enabled=settings.usage_refresh_enabled,
        interval_seconds=settings.usage_refresh_interval_seconds,
    )
    await firecrawl_refresh_scheduler.start()
    if settings.metrics_enabled and PROMETHEUS_AVAILABLE:
        import uvicorn

        scrape_registry = make_scrape_registry()
        prometheus_module = import_module("prometheus_client")
        make_asgi_app = getattr(prometheus_module, "make_asgi_app")
        metrics_app = make_asgi_app(registry=scrape_registry)
        config = uvicorn.Config(metrics_app, host="0.0.0.0", port=settings.metrics_port, log_level="warning")
        metrics_server = uvicorn.Server(config)

        async def _serve_metrics(srv: _MetricsServer) -> None:
            try:
                await srv.serve()
            except SystemExit as exc:
                if _is_benign_metrics_bind_failure(exc):
                    logger.info(
                        "Metrics port %d unavailable (another worker likely serves metrics)",
                        settings.metrics_port,
                    )
                else:
                    raise
            except OSError as exc:
                if _is_benign_metrics_bind_failure(exc):
                    logger.info(
                        "Metrics port %d already bound (another worker serves metrics)",
                        settings.metrics_port,
                    )
                else:
                    raise

        metrics_server_task = asyncio.create_task(_serve_metrics(metrics_server))
    elif settings.metrics_enabled:
        logger.warning("Metrics endpoint enabled but prometheus-client is not installed")

    from app.core.cache.invalidation import (
        NAMESPACE_FIREWALL,
        CacheInvalidationPoller,
        set_cache_invalidation_poller,
    )
    from app.core.middleware.firewall_cache import get_firewall_ip_cache

    cache_poller = CacheInvalidationPoller(SessionLocal)
    cache_poller.on_invalidation(NAMESPACE_FIREWALL, get_firewall_ip_cache().invalidate_all)
    set_cache_invalidation_poller(cache_poller)
    await cache_poller.start()

    startup_module._startup_complete = True

    try:
        yield
    finally:
        shutdown_state.set_draining(True)
        drained = await shutdown_state.wait_for_in_flight_drain(timeout_seconds=settings.shutdown_drain_timeout_seconds)
        if not drained:
            logger.warning("Drain timeout reached, proceeding with shutdown")

        if metrics_server is not None:
            metrics_server.should_exit = True

        await cache_poller.stop()
        await firecrawl_refresh_scheduler.stop()
        try:
            await close_http_client()
        finally:
            try:
                if metrics_server_task is not None:
                    await asyncio.wait_for(metrics_server_task, timeout=5)
            except TimeoutError:
                logger.warning("Timed out waiting for metrics server shutdown")
            except Exception:
                logger.exception("Metrics server stopped with an error")
            finally:
                shutdown_state.reset()
                mark_process_dead()
                await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_memory_monitor(
        warning_threshold_mb=settings.memory_warning_threshold_mb,
        reject_threshold_mb=settings.memory_reject_threshold_mb,
    )
    app = FastAPI(
        title="firecrawl-lb",
        version="0.1.0",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True},
    )

    app.add_middleware(cast(Any, InFlightMiddleware))
    add_dashboard_auth_proxy_middleware(app)
    add_request_decompression_middleware(app)
    add_request_id_middleware(app)
    add_api_firewall_middleware(app)
    app.add_middleware(cast(Any, MetricsMiddleware), enabled=settings.metrics_enabled)
    if settings.backpressure_max_concurrent_requests > 0:
        app.add_middleware(
            cast(Any, BackpressureMiddleware),
            max_concurrent=settings.backpressure_max_concurrent_requests,
        )
    proxy_http_limit = settings.bulkhead_proxy_http_limit
    assert proxy_http_limit is not None
    app.add_middleware(
        cast(Any, BulkheadMiddleware),
        bulkhead=get_bulkhead(
            proxy_http_limit=proxy_http_limit,
            dashboard_limit=settings.bulkhead_dashboard_limit,
        ),
    )
    add_app_version_middleware(app)
    add_exception_handlers(app)

    app.include_router(firecrawl_api.router)
    app.include_router(audit_api.router)
    app.include_router(runtime_api.router)
    app.include_router(dashboard_auth_api.router)
    app.include_router(settings_api.router)
    app.include_router(firewall_api.router)
    app.include_router(health_api.router)

    static_dir = Path(__file__).parent / "static"
    index_html = static_dir / "index.html"
    static_root = static_dir.resolve()
    frontend_build_hint = "Frontend assets are missing. Run `cd frontend && bun run build`."
    excluded_prefixes = ("api/", "v2/", "health")

    def _is_static_asset_path(path: str) -> bool:
        if path.startswith("assets/"):
            return True
        last_segment = path.rsplit("/", maxsplit=1)[-1]
        return "." in last_segment

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str = ""):
        normalized = path.lstrip("/")
        if normalized and any(
            normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in excluded_prefixes
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        if normalized:
            candidate = _resolve_static_asset_path(static_root, normalized)
            if candidate is not None:
                return FileResponse(candidate)
            if _is_static_asset_path(normalized):
                raise HTTPException(status_code=404, detail="Not Found")

        if not index_html.is_file():
            raise HTTPException(status_code=503, detail=frontend_build_hint)

        return FileResponse(index_html, media_type="text/html")

    return app


app = create_app()
