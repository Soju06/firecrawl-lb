from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditLogsService
from app.modules.dashboard_auth.repository import DashboardAuthRepository
from app.modules.dashboard_auth.service import (
    DashboardAuthRepositoryProtocol,
    DashboardAuthService,
    get_dashboard_session_store,
)
from app.modules.firewall.repository import FirewallRepository
from app.modules.firewall.service import FirewallRepositoryPort, FirewallService


@dataclass(slots=True)
class AuditContext:
    session: AsyncSession
    repository: AuditRepository
    service: AuditLogsService


@dataclass(slots=True)
class DashboardAuthContext:
    session: AsyncSession
    repository: DashboardAuthRepository
    service: DashboardAuthService


@dataclass(slots=True)
class FirewallContext:
    session: AsyncSession
    repository: FirewallRepository
    service: FirewallService


def get_audit_context(
    session: AsyncSession = Depends(get_session),
) -> AuditContext:
    repository = AuditRepository(session)
    service = AuditLogsService(repository)
    return AuditContext(session=session, repository=repository, service=service)


def get_dashboard_auth_context(
    session: AsyncSession = Depends(get_session),
) -> DashboardAuthContext:
    repository = DashboardAuthRepository(session)
    service = DashboardAuthService(cast(DashboardAuthRepositoryProtocol, repository), get_dashboard_session_store())
    return DashboardAuthContext(session=session, repository=repository, service=service)


def get_firewall_context(
    session: AsyncSession = Depends(get_session),
) -> FirewallContext:
    repository = FirewallRepository(session)
    service = FirewallService(cast(FirewallRepositoryPort, repository))
    return FirewallContext(session=session, repository=repository, service=service)
