from __future__ import annotations

import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp
import certifi

from app.core.config.settings import get_settings

_http_session: aiohttp.ClientSession | None = None


def _build_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


async def init_http_client() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        settings = get_settings()
        connector = aiohttp.TCPConnector(
            limit=settings.http_connector_limit,
            limit_per_host=settings.http_connector_limit_per_host,
            ssl=_build_ssl_context(),
        )
        _http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=None),
            trust_env=True,
        )
    return _http_session


async def close_http_client() -> None:
    global _http_session
    if _http_session is not None:
        await _http_session.close()
        _http_session = None


@asynccontextmanager
async def lease_http_session(session: aiohttp.ClientSession | None = None) -> AsyncIterator[aiohttp.ClientSession]:
    if session is not None:
        yield session
        return
    yield await init_http_client()


def get_http_client() -> aiohttp.ClientSession:
    if _http_session is None or _http_session.closed:
        raise RuntimeError("HTTP client not initialized")
    return _http_session
