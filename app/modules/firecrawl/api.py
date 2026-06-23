from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.firecrawl.client import create_firecrawl_client
from app.modules.firecrawl.repository import FirecrawlRepository
from app.modules.firecrawl.routing import NoFirecrawlAccountAvailable
from app.modules.firecrawl.service import FirecrawlProxyService, no_account_response

router = APIRouter(prefix="/v2", tags=["firecrawl"])


def get_firecrawl_repository(session: AsyncSession = Depends(get_session)) -> FirecrawlRepository:
    return FirecrawlRepository(session)


@router.post("/scrape")
async def scrape(request: Request, repository: FirecrawlRepository = Depends(get_firecrawl_repository)) -> Response:
    return await _proxy_firecrawl_request("scrape", request, repository)


@router.post("/map")
async def map_urls(request: Request, repository: FirecrawlRepository = Depends(get_firecrawl_repository)) -> Response:
    return await _proxy_firecrawl_request("map", request, repository)


@router.post("/search")
async def search(request: Request, repository: FirecrawlRepository = Depends(get_firecrawl_repository)) -> Response:
    return await _proxy_firecrawl_request("search", request, repository)


async def _proxy_firecrawl_request(endpoint: str, request: Request, repository: FirecrawlRepository) -> Response:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Firecrawl request body must be a JSON object")
    service = FirecrawlProxyService(repository)
    try:
        upstream = await service.proxy(
            endpoint,
            payload,
            create_firecrawl_client(),
            params=_string_query_params(request.query_params),
        )
    except NoFirecrawlAccountAvailable as exc:
        return JSONResponse(status_code=503, content=no_account_response(exc))
    if upstream.json_body is not None:
        return JSONResponse(status_code=upstream.status, content=upstream.json_body)
    return Response(
        content=upstream.text_body or "",
        status_code=upstream.status,
        media_type=_response_media_type(upstream.headers),
    )


def _string_query_params(query_params: Mapping[str, str]) -> dict[str, str] | None:
    params = dict(query_params)
    return params or None


def _response_media_type(headers: Mapping[str, str]) -> str | None:
    return headers.get("content-type") or headers.get("Content-Type")
