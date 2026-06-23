from __future__ import annotations

import os
from importlib import import_module
from typing import Protocol


class CollectorRegistryLike(Protocol):
    pass


class CounterLike(Protocol):
    def inc(self, amount: float = 1) -> None: ...
    def labels(self, *args: str, **kwargs: str) -> "CounterLike": ...


class GaugeLike(Protocol):
    def inc(self, amount: float = 1) -> None: ...
    def dec(self, amount: float = 1) -> None: ...
    def set(self, value: float) -> None: ...
    def labels(self, *args: str, **kwargs: str) -> "GaugeLike": ...


class HistogramLike(Protocol):
    def observe(self, amount: float) -> None: ...
    def labels(self, *args: str, **kwargs: str) -> "HistogramLike": ...


try:
    prometheus_client = import_module("prometheus_client")
except ImportError:
    prometheus_client = None

PROMETHEUS_AVAILABLE = prometheus_client is not None
MULTIPROCESS_MODE = bool(os.environ.get("PROMETHEUS_MULTIPROC_DIR"))

if PROMETHEUS_AVAILABLE:
    CollectorRegistry = getattr(prometheus_client, "CollectorRegistry")
    Counter = getattr(prometheus_client, "Counter")
    Gauge = getattr(prometheus_client, "Gauge")
    Histogram = getattr(prometheus_client, "Histogram")

    REGISTRY = CollectorRegistry(auto_describe=True)

    requests_total = Counter(
        "firecrawl_lb_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
        registry=REGISTRY,
    )
    request_duration_seconds = Histogram(
        "firecrawl_lb_request_duration_seconds",
        "HTTP request duration",
        ["method", "path"],
        registry=REGISTRY,
    )
    upstream_requests_total = Counter(
        "firecrawl_lb_upstream_requests_total",
        "Total Firecrawl upstream requests",
        ["account_id", "status"],
        registry=REGISTRY,
    )
    upstream_request_duration_seconds = Histogram(
        "firecrawl_lb_upstream_request_duration_seconds",
        "Firecrawl upstream request duration",
        registry=REGISTRY,
    )

    _gauge_kwargs: dict[str, str] = {}
    if MULTIPROCESS_MODE:
        _gauge_kwargs["multiprocess_mode"] = "livesum"

    active_connections = Gauge(
        "firecrawl_lb_active_connections",
        "Active HTTP connections",
        registry=REGISTRY,
        **_gauge_kwargs,
    )
    rate_limit_hits_total = Counter(
        "firecrawl_lb_rate_limit_hits_total",
        "Rate limit hits",
        ["type"],
        registry=REGISTRY,
    )
    circuit_breaker_state = Gauge(
        "firecrawl_lb_circuit_breaker_state",
        "Circuit breaker state (0=closed, 1=open, 2=half-open)",
        ["service"],
        registry=REGISTRY,
        **({"multiprocess_mode": "liveall"} if MULTIPROCESS_MODE else {}),
    )
    accounts_total = Gauge(
        "firecrawl_lb_accounts_total",
        "Total Firecrawl accounts by status",
        ["status"],
        registry=REGISTRY,
        **({"multiprocess_mode": "liveall"} if MULTIPROCESS_MODE else {}),
    )

    def make_scrape_registry() -> CollectorRegistryLike:
        if MULTIPROCESS_MODE:
            _multiprocess = import_module("prometheus_client.multiprocess")
            registry = CollectorRegistry()
            _multiprocess.MultiProcessCollector(registry)
            return registry
        return REGISTRY

    def mark_process_dead() -> None:
        if MULTIPROCESS_MODE:
            try:
                _multiprocess = import_module("prometheus_client.multiprocess")
                _multiprocess.mark_process_dead(os.getpid())
            except (ImportError, AttributeError):
                pass

else:
    REGISTRY: CollectorRegistryLike | None = None
    requests_total: CounterLike | None = None
    request_duration_seconds: HistogramLike | None = None
    upstream_requests_total: CounterLike | None = None
    upstream_request_duration_seconds: HistogramLike | None = None
    active_connections: GaugeLike | None = None
    rate_limit_hits_total: CounterLike | None = None
    circuit_breaker_state: GaugeLike | None = None
    accounts_total: GaugeLike | None = None

    def make_scrape_registry() -> None:
        return None

    def mark_process_dead() -> None:
        return None


__all__ = [
    "MULTIPROCESS_MODE",
    "PROMETHEUS_AVAILABLE",
    "REGISTRY",
    "CollectorRegistryLike",
    "CounterLike",
    "GaugeLike",
    "HistogramLike",
    "accounts_total",
    "active_connections",
    "circuit_breaker_state",
    "make_scrape_registry",
    "mark_process_dead",
    "rate_limit_hits_total",
    "request_duration_seconds",
    "requests_total",
    "upstream_request_duration_seconds",
    "upstream_requests_total",
]
