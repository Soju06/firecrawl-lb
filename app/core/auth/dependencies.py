from __future__ import annotations

import logging

from fastapi import Request

from app.core.auth.dashboard_mode import DashboardAuthMode, get_dashboard_request_auth
from app.core.config.settings import get_settings
from app.core.config.settings_cache import get_settings_cache
from app.core.exceptions import DashboardAuthError
from app.core.request_locality import is_local_request
from app.modules.dashboard_auth.service import DASHBOARD_SESSION_COOKIE, get_dashboard_session_store

logger = logging.getLogger(__name__)


def set_dashboard_error_format(request: Request) -> None:
    request.state.error_format = "dashboard"


async def validate_dashboard_session(request: Request) -> None:
    request_auth = get_dashboard_request_auth(request)
    if request_auth is not None:
        return

    settings = await get_settings_cache().get()
    password_required = bool(settings.password_hash)
    requires_auth = password_required or settings.totp_required_on_login
    if get_dashboard_request_auth_mode() == DashboardAuthMode.TRUSTED_HEADER and not requires_auth:
        raise DashboardAuthError("Reverse proxy authentication is required", code="proxy_auth_required")
    if not requires_auth:
        if not is_local_request(request):
            raise DashboardAuthError(
                "Remote bootstrap is required before dashboard access is allowed",
                code="bootstrap_required",
            )
        return

    if not password_required and settings.totp_required_on_login:
        logger.warning(
            "dashboard_auth_migration_inconsistency password_hash is NULL"
            " while totp_required_on_login=true metric=dashboard_auth_migration_inconsistency"
        )

    session_id = request.cookies.get(DASHBOARD_SESSION_COOKIE)
    state = get_dashboard_session_store().get(session_id)
    if state is None:
        raise DashboardAuthError("Authentication is required")
    if password_required and not state.password_verified:
        raise DashboardAuthError("Authentication is required")
    if settings.totp_required_on_login and not state.totp_verified:
        raise DashboardAuthError("TOTP verification is required for dashboard access", code="totp_required")


def get_dashboard_request_auth_mode() -> DashboardAuthMode:
    return get_settings().dashboard_auth_mode
