from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.firecrawl.admin_service import (
    FirecrawlAccountConflictError,
    FirecrawlAccountNotFoundError,
    FirecrawlAdminService,
    FirecrawlCredentialConflictError,
    FirecrawlCredentialNotFoundError,
)
from app.modules.firecrawl.client import create_firecrawl_client
from app.modules.firecrawl.repository import FirecrawlRepository
from app.modules.firecrawl.routing import NoFirecrawlAccountAvailable
from app.modules.firecrawl.schemas import (
    FirecrawlAccountCreateRequest,
    FirecrawlAccountResponse,
    FirecrawlAccountsResponse,
    FirecrawlAccountUpdateRequest,
    FirecrawlCredentialCreateRequest,
    FirecrawlCredentialResponse,
    FirecrawlCredentialUpdateRequest,
)
from app.modules.firecrawl.service import FirecrawlProxyService, no_account_response

router = APIRouter(prefix="/v2", tags=["firecrawl"])


def get_firecrawl_repository(session: AsyncSession = Depends(get_session)) -> FirecrawlRepository:
    return FirecrawlRepository(session)


def get_firecrawl_admin_service(
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> FirecrawlAdminService:
    return FirecrawlAdminService(repository)


@router.get("/admin/firecrawl/accounts", response_model=FirecrawlAccountsResponse)
async def list_admin_firecrawl_accounts(
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountsResponse:
    return await service.list_accounts()


@router.post(
    "/admin/firecrawl/accounts",
    response_model=FirecrawlAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_firecrawl_account(
    payload: FirecrawlAccountCreateRequest,
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountResponse:
    try:
        return await service.create_account(payload)
    except FirecrawlAccountConflictError as exc:
        raise HTTPException(status_code=409, detail="Firecrawl account already exists") from exc


@router.get("/admin/firecrawl/accounts/{account_id}", response_model=FirecrawlAccountResponse)
async def get_admin_firecrawl_account(
    account_id: str,
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountResponse:
    try:
        return await service.get_account(account_id)
    except FirecrawlAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Firecrawl account not found") from exc


@router.patch("/admin/firecrawl/accounts/{account_id}", response_model=FirecrawlAccountResponse)
async def update_admin_firecrawl_account(
    account_id: str,
    payload: FirecrawlAccountUpdateRequest,
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountResponse:
    try:
        return await service.update_account(account_id, payload)
    except FirecrawlAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Firecrawl account not found") from exc


@router.post(
    "/admin/firecrawl/accounts/{account_id}/credentials",
    response_model=FirecrawlCredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_firecrawl_credential(
    account_id: str,
    payload: FirecrawlCredentialCreateRequest,
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlCredentialResponse:
    try:
        return await service.create_credential(account_id, payload)
    except FirecrawlAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Firecrawl account not found") from exc
    except FirecrawlCredentialConflictError as exc:
        raise HTTPException(status_code=409, detail="Firecrawl credential already exists") from exc


@router.patch(
    "/admin/firecrawl/accounts/{account_id}/credentials/{credential_id}",
    response_model=FirecrawlCredentialResponse,
)
async def update_admin_firecrawl_credential(
    account_id: str,
    credential_id: str,
    payload: FirecrawlCredentialUpdateRequest,
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlCredentialResponse:
    try:
        return await service.update_credential(account_id, credential_id, payload)
    except FirecrawlAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Firecrawl account not found") from exc
    except FirecrawlCredentialNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Firecrawl credential not found") from exc


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
