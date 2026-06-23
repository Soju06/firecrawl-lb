from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import set_dashboard_error_format, validate_dashboard_session
from app.core.config.settings import get_settings
from app.modules.settings.schemas import FirecrawlRuntimeSettingsResponse

router = APIRouter(
    prefix="/api/settings",
    tags=["dashboard"],
    dependencies=[Depends(validate_dashboard_session), Depends(set_dashboard_error_format)],
)


def _mask_database_url(database_url: str) -> str:
    scheme_separator = "://"
    if scheme_separator not in database_url or "@" not in database_url:
        return database_url
    scheme, remainder = database_url.split(scheme_separator, 1)
    _credentials, host_part = remainder.rsplit("@", 1)
    return f"{scheme}{scheme_separator}***@{host_part}"


@router.get("/firecrawl-runtime", response_model=FirecrawlRuntimeSettingsResponse)
async def get_firecrawl_runtime_settings() -> FirecrawlRuntimeSettingsResponse:
    settings = get_settings()
    return FirecrawlRuntimeSettingsResponse(
        refresh_scheduler_enabled=settings.usage_refresh_enabled,
        data_dir=str(settings.data_dir),
        database_url_masked=_mask_database_url(settings.database_url),
        encryption_key_file=str(settings.encryption_key_file),
    )
