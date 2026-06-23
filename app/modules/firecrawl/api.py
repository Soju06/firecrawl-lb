from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dashboard_mode import get_dashboard_request_auth
from app.core.auth.dependencies import validate_dashboard_session
from app.core.exceptions import DashboardAuthError
from app.db.session import get_session
from app.modules.dashboard_auth.service import DASHBOARD_SESSION_COOKIE
from app.modules.firecrawl.admin_service import (
    FirecrawlAccountConflictError,
    FirecrawlAccountNotFoundError,
    FirecrawlAdminService,
    FirecrawlCredentialConflictError,
    FirecrawlCredentialNotFoundError,
)
from app.modules.firecrawl.client import FirecrawlUpstreamResponse, create_firecrawl_client
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
    FirecrawlJobsResponse,
    FirecrawlOverviewResponse,
    FirecrawlRequestLogsResponse,
)
from app.modules.firecrawl.service import FirecrawlProxyService, no_account_response

router = APIRouter(prefix="/v2", tags=["firecrawl"])


def get_firecrawl_repository(session: AsyncSession = Depends(get_session)) -> FirecrawlRepository:
    return FirecrawlRepository(session)


def get_firecrawl_admin_service(
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> FirecrawlAdminService:
    return FirecrawlAdminService(repository)


async def require_firecrawl_admin(request: Request) -> None:
    await validate_dashboard_session(request)
    if get_dashboard_request_auth(request) is None and not request.cookies.get(DASHBOARD_SESSION_COOKIE):
        raise DashboardAuthError("Authentication is required")


@router.get("/admin/firecrawl/accounts", response_model=FirecrawlAccountsResponse)
async def list_admin_firecrawl_accounts(
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountsResponse:
    del _admin
    return await service.list_accounts()


@router.get("/admin/firecrawl/jobs", response_model=FirecrawlJobsResponse)
async def list_admin_firecrawl_jobs(
    endpoint: Literal["crawl", "batch_scrape"] | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlJobsResponse:
    del _admin
    return await service.list_jobs(endpoint=endpoint, status=status, limit=limit, offset=offset)


@router.get("/admin/firecrawl/logs", response_model=FirecrawlRequestLogsResponse)
async def list_admin_firecrawl_logs(
    endpoint: Literal["scrape", "map", "search"] | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlRequestLogsResponse:
    del _admin
    return await service.list_logs(endpoint=endpoint, status=status, limit=limit, offset=offset)


@router.get("/admin/firecrawl/overview", response_model=FirecrawlOverviewResponse)
async def get_admin_firecrawl_overview(
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlOverviewResponse:
    del _admin
    return await service.get_overview()


@router.post(
    "/admin/firecrawl/accounts",
    response_model=FirecrawlAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_firecrawl_account(
    payload: FirecrawlAccountCreateRequest,
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountResponse:
    del _admin
    try:
        return await service.create_account(payload)
    except FirecrawlAccountConflictError as exc:
        raise HTTPException(status_code=409, detail="Firecrawl account already exists") from exc


@router.get("/admin/firecrawl/accounts/{account_id}", response_model=FirecrawlAccountResponse)
async def get_admin_firecrawl_account(
    account_id: str,
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountResponse:
    del _admin
    try:
        return await service.get_account(account_id)
    except FirecrawlAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Firecrawl account not found") from exc


@router.patch("/admin/firecrawl/accounts/{account_id}", response_model=FirecrawlAccountResponse)
async def update_admin_firecrawl_account(
    account_id: str,
    payload: FirecrawlAccountUpdateRequest,
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlAccountResponse:
    del _admin
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
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlCredentialResponse:
    del _admin
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
    _admin: None = Depends(require_firecrawl_admin),
    service: FirecrawlAdminService = Depends(get_firecrawl_admin_service),
) -> FirecrawlCredentialResponse:
    del _admin
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


@router.post("/crawl")
async def submit_crawl(
    request: Request,
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> Response:
    return await _submit_firecrawl_job("crawl", "/v2/crawl", request, repository)


@router.post("/batch/scrape")
async def submit_batch_scrape(
    request: Request,
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> Response:
    return await _submit_firecrawl_job("batch_scrape", "/v2/batch/scrape", request, repository)


@router.get("/crawl/{job_id}")
async def get_crawl_job(job_id: str, repository: FirecrawlRepository = Depends(get_firecrawl_repository)) -> Response:
    return await _proxy_firecrawl_job_operation("crawl", f"/v2/crawl/{job_id}", job_id, "GET", repository)


@router.get("/batch/scrape/{job_id}")
async def get_batch_scrape_job(
    job_id: str,
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> Response:
    return await _proxy_firecrawl_job_operation("batch_scrape", f"/v2/batch/scrape/{job_id}", job_id, "GET", repository)


@router.delete("/crawl/{job_id}")
async def cancel_crawl_job(
    job_id: str,
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> Response:
    return await _proxy_firecrawl_job_operation("crawl", f"/v2/crawl/{job_id}", job_id, "DELETE", repository)


@router.delete("/batch/scrape/{job_id}")
async def cancel_batch_scrape_job(
    job_id: str,
    repository: FirecrawlRepository = Depends(get_firecrawl_repository),
) -> Response:
    return await _proxy_firecrawl_job_operation(
        "batch_scrape",
        f"/v2/batch/scrape/{job_id}",
        job_id,
        "DELETE",
        repository,
    )


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


async def _submit_firecrawl_job(
    endpoint: str,
    path: str,
    request: Request,
    repository: FirecrawlRepository,
) -> Response:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Firecrawl request body must be a JSON object")
    service = FirecrawlProxyService(repository)
    try:
        upstream = await service.submit_job(
            endpoint,
            path,
            payload,
            create_firecrawl_client(),
            params=_string_query_params(request.query_params),
        )
    except NoFirecrawlAccountAvailable as exc:
        return JSONResponse(status_code=503, content=no_account_response(exc))
    return _upstream_response(upstream)


async def _proxy_firecrawl_job_operation(
    endpoint: str,
    path: str,
    job_id: str,
    method: str,
    repository: FirecrawlRepository,
) -> Response:
    service = FirecrawlProxyService(repository)
    upstream = await service.proxy_job_operation(
        endpoint=endpoint,
        upstream_path=path,
        upstream_job_id=job_id,
        method=method,
        client=create_firecrawl_client(),
    )
    if upstream is None:
        raise HTTPException(status_code=404, detail="Firecrawl job not found")
    return _upstream_response(upstream)


def _upstream_response(upstream: FirecrawlUpstreamResponse) -> Response:
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
