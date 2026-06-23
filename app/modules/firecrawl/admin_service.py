from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.core.crypto import TokenEncryptor
from app.db.models import (
    FirecrawlAccountRecord,
    FirecrawlCredentialRecord,
    FirecrawlJobRecord,
    FirecrawlRequestLogRecord,
)
from app.modules.firecrawl.repository import FirecrawlRepository
from app.modules.firecrawl.schemas import (
    FirecrawlAccountCreateRequest,
    FirecrawlAccountResponse,
    FirecrawlAccountsByStatusResponse,
    FirecrawlAccountsResponse,
    FirecrawlAccountUpdateRequest,
    FirecrawlCredentialCreateRequest,
    FirecrawlCredentialResponse,
    FirecrawlCredentialUpdateRequest,
    FirecrawlEndpointBreakdownResponse,
    FirecrawlJobResponse,
    FirecrawlJobsResponse,
    FirecrawlOverviewResponse,
    FirecrawlRecentRequestsResponse,
    FirecrawlRequestLogResponse,
    FirecrawlRequestLogsResponse,
)

ACCOUNT_STATUSES = ("active", "rate_limited", "credit_exhausted", "paused")
SYNC_ENDPOINTS = ("scrape", "map", "search")
JOB_ENDPOINTS = ("crawl", "batch_scrape")
ACTIVE_JOB_STATUSES = {"submitted"}


class FirecrawlAccountNotFoundError(Exception):
    pass


class FirecrawlCredentialNotFoundError(Exception):
    pass


class FirecrawlAccountConflictError(Exception):
    pass


class FirecrawlCredentialConflictError(Exception):
    pass


class FirecrawlAdminService:
    def __init__(self, repository: FirecrawlRepository, encryptor: TokenEncryptor | None = None) -> None:
        self._repository = repository
        self._encryptor = encryptor or TokenEncryptor()

    async def list_accounts(self) -> FirecrawlAccountsResponse:
        accounts = await self._repository.list_account_records()
        return FirecrawlAccountsResponse(accounts=[_account_response(account) for account in accounts])

    async def list_jobs(
        self,
        *,
        endpoint: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> FirecrawlJobsResponse:
        jobs = await self._repository.list_job_records(endpoint=endpoint, status=status, limit=limit, offset=offset)
        return FirecrawlJobsResponse(jobs=[_job_response(job) for job in jobs])

    async def list_logs(
        self,
        *,
        endpoint: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> FirecrawlRequestLogsResponse:
        logs = await self._repository.list_request_logs(endpoint=endpoint, status=status, limit=limit, offset=offset)
        return FirecrawlRequestLogsResponse(logs=[_request_log_response(log) for log in logs])

    async def get_overview(self) -> FirecrawlOverviewResponse:
        accounts = await self._repository.list_account_records()
        jobs = await self._repository.list_job_records(limit=10_000)
        logs = await self._repository.list_request_logs(limit=10_000)
        accounts_by_status = {status: 0 for status in ACCOUNT_STATUSES}
        for account in accounts:
            if account.status in accounts_by_status:
                accounts_by_status[account.status] += 1
        sync_counts = _count_by_endpoint(logs, SYNC_ENDPOINTS)
        job_counts = _count_by_endpoint(jobs, JOB_ENDPOINTS)
        return FirecrawlOverviewResponse(
            total_accounts=len(accounts),
            active_accounts=accounts_by_status["active"],
            total_remaining_credits=sum(account.remaining_credits_live or 0 for account in accounts),
            total_budget_credits=sum(
                account.monthly_budget_credits or account.plan_credits_live or 0 for account in accounts
            ),
            accounts_by_status=FirecrawlAccountsByStatusResponse(
                active=accounts_by_status["active"],
                rate_limited=accounts_by_status["rate_limited"],
                credit_exhausted=accounts_by_status["credit_exhausted"],
                paused=accounts_by_status["paused"],
            ),
            active_jobs=sum(1 for job in jobs if job.status in ACTIVE_JOB_STATUSES),
            recent_requests=FirecrawlRecentRequestsResponse(
                total=len(logs),
                success=sum(1 for log in logs if log.status == "success"),
                error=sum(1 for log in logs if log.status == "error"),
            ),
            endpoint_breakdown=FirecrawlEndpointBreakdownResponse(
                scrape=sync_counts["scrape"],
                map=sync_counts["map"],
                search=sync_counts["search"],
                crawl=job_counts["crawl"],
                batch_scrape=job_counts["batch_scrape"],
            ),
        )

    async def get_account(self, account_id: str) -> FirecrawlAccountResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        return _account_response(account)

    async def create_account(self, payload: FirecrawlAccountCreateRequest) -> FirecrawlAccountResponse:
        existing = await self._repository.get_account_record(payload.id)
        if existing is not None:
            raise FirecrawlAccountConflictError
        account = FirecrawlAccountRecord(
            id=payload.id,
            team_label=payload.team_label,
            plan_type=payload.plan_type,
            monthly_budget_credits=payload.monthly_budget_credits,
            remaining_credits_live=payload.remaining_credits_live,
            plan_credits_live=payload.plan_credits_live,
            rpm_limit=payload.rpm_limit,
            queue_max_concurrency=payload.max_concurrency,
        )
        self._repository.add_account_record(account)
        try:
            await self._repository.commit()
        except IntegrityError as exc:
            raise FirecrawlAccountConflictError from exc
        return _account_response(account)

    async def update_account(self, account_id: str, payload: FirecrawlAccountUpdateRequest) -> FirecrawlAccountResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if field_name == "max_concurrency":
                account.queue_max_concurrency = value
                continue
            setattr(account, field_name, value)
        await self._repository.commit()
        return _account_response(account)

    async def create_credential(
        self,
        account_id: str,
        payload: FirecrawlCredentialCreateRequest,
    ) -> FirecrawlCredentialResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        existing = await self._repository.get_credential_record(payload.id)
        if existing is not None:
            raise FirecrawlCredentialConflictError
        credential = FirecrawlCredentialRecord(
            id=payload.id,
            account_id=account_id,
            name=payload.name,
            api_key_encrypted=self._encryptor.encrypt(payload.api_key),
            status=payload.status,
        )
        self._repository.add_credential_record(credential)
        try:
            await self._repository.commit()
        except IntegrityError as exc:
            raise FirecrawlCredentialConflictError from exc
        return _credential_response(credential)

    async def update_credential(
        self,
        account_id: str,
        credential_id: str,
        payload: FirecrawlCredentialUpdateRequest,
    ) -> FirecrawlCredentialResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        credential = await self._repository.get_credential_record(credential_id)
        if credential is None or credential.account_id != account_id:
            raise FirecrawlCredentialNotFoundError
        credential.status = payload.status
        await self._repository.commit()
        return _credential_response(credential)


def _account_response(account: FirecrawlAccountRecord) -> FirecrawlAccountResponse:
    credentials = [] if "credentials" in inspect(account).unloaded else account.credentials
    return FirecrawlAccountResponse(
        id=account.id,
        team_label=account.team_label,
        plan_type=account.plan_type,
        status=account.status,
        monthly_budget_credits=account.monthly_budget_credits,
        remaining_credits_live=account.remaining_credits_live,
        plan_credits_live=account.plan_credits_live,
        rpm_limit=account.rpm_limit,
        max_concurrency=account.queue_max_concurrency,
        cooldown_until=account.cooldown_until,
        credentials=[_credential_response(credential) for credential in credentials],
    )


def _credential_response(credential: FirecrawlCredentialRecord) -> FirecrawlCredentialResponse:
    return FirecrawlCredentialResponse(
        id=credential.id,
        name=credential.name,
        status=credential.status,
    )


def _job_response(job: FirecrawlJobRecord) -> FirecrawlJobResponse:
    return FirecrawlJobResponse(
        id=job.id,
        account_id=job.account_id,
        credential_id=job.credential_id,
        endpoint=job.endpoint,
        upstream_job_id=job.upstream_job_id,
        status=job.status,
        estimated_credits_reserved=job.estimated_credits_reserved,
        credits_used_final=job.credits_used_final,
        created_at=job.created_at,
        completed_at=job.completed_at,
        last_polled_at=job.last_polled_at,
    )


def _request_log_response(log: FirecrawlRequestLogRecord) -> FirecrawlRequestLogResponse:
    return FirecrawlRequestLogResponse(
        id=log.id,
        account_id=log.account_id,
        credential_id=log.credential_id,
        endpoint=log.endpoint,
        upstream_job_id=log.upstream_job_id,
        status=log.status,
        upstream_status_code=log.upstream_status_code,
        estimated_credits_pre=log.estimated_credits_pre,
        credits_used_final=log.credits_used_final,
        latency_ms=log.latency_ms,
        error_code=log.error_code,
        error_message=log.error_message,
        created_at=log.requested_at,
    )


def _count_by_endpoint(
    records: list[FirecrawlJobRecord] | list[FirecrawlRequestLogRecord],
    endpoints: tuple[str, ...],
) -> dict[str, int]:
    counts = {endpoint: 0 for endpoint in endpoints}
    for record in records:
        if record.endpoint in counts:
            counts[record.endpoint] += 1
    return counts
