from __future__ import annotations

from ipaddress import ip_address

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from app.db.session import get_session
from app.modules.health.schemas import HealthCheckResponse, HealthResponse

router = APIRouter(tags=["health"])


def _is_internal_client_host(client_host: str | None) -> bool:
    if client_host in {"localhost"}:
        return True
    if client_host is None:
        return False
    try:
        address = ip_address(client_host)
    except ValueError:
        return False
    return address.is_loopback


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/live", response_model=HealthCheckResponse)
async def health_live() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok")


@router.get("/health/ready", response_model=HealthCheckResponse)
async def health_ready() -> HealthCheckResponse:
    import app.core.draining as draining_module

    if getattr(draining_module, "_draining", False):
        raise HTTPException(status_code=503, detail="Service is draining")

    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
            return HealthCheckResponse(status="ok", checks={"database": "ok"})
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Service unavailable") from exc

    raise HTTPException(status_code=503, detail="Service unavailable")


@router.post("/internal/drain/start", include_in_schema=False)
async def start_internal_drain(request: Request) -> HealthCheckResponse:
    client_host = request.client.host if request.client is not None else None
    if not _is_internal_client_host(client_host):
        raise HTTPException(status_code=403, detail="Internal access required")

    import app.core.shutdown as shutdown_state

    shutdown_state.set_draining(True)
    return HealthCheckResponse(status="ok", checks={"draining": "ok"})


@router.post("/internal/drain/stop", include_in_schema=False)
async def stop_internal_drain(request: Request) -> HealthCheckResponse:
    client_host = request.client.host if request.client is not None else None
    if not _is_internal_client_host(client_host):
        raise HTTPException(status_code=403, detail="Internal access required")

    import app.core.shutdown as shutdown_state

    shutdown_state.set_draining(False)
    return HealthCheckResponse(status="ok", checks={"draining": "false"})


@router.get("/internal/drain/status", include_in_schema=False)
async def internal_drain_status(request: Request) -> HealthCheckResponse:
    client_host = request.client.host if request.client is not None else None
    if not _is_internal_client_host(client_host):
        raise HTTPException(status_code=403, detail="Internal access required")

    import app.core.shutdown as shutdown_state

    return HealthCheckResponse(
        status="ok",
        checks={
            "draining": str(shutdown_state.is_draining()).lower(),
            "in_flight": str(shutdown_state.get_in_flight()),
        },
    )
