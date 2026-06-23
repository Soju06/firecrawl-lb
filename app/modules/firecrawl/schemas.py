from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

ACCOUNT_STATUS_PATTERN = r"^(active|rate_limited|credit_exhausted|paused|invalid)$"
CREDENTIAL_STATUS_PATTERN = r"^(active|paused|invalid)$"
JOB_ENDPOINT_PATTERN = r"^(crawl|batch_scrape)$"
REQUEST_LOG_ENDPOINT_PATTERN = r"^(scrape|map|search)$"


class FirecrawlAdminModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    @field_serializer(
        "cooldown_until",
        "created_at",
        "completed_at",
        "last_polled_at",
        check_fields=False,
        when_used="json",
    )
    def serialize_datetime_as_utc(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.isoformat()
            return value.isoformat().replace("+00:00", "Z")
        return None


class FirecrawlCredentialResponse(FirecrawlAdminModel):
    id: str
    name: str | None
    status: str = Field(pattern=CREDENTIAL_STATUS_PATTERN)


class FirecrawlAccountResponse(FirecrawlAdminModel):
    id: str
    team_label: str
    plan_type: str
    status: str = Field(pattern=ACCOUNT_STATUS_PATTERN)
    monthly_budget_credits: int | None
    remaining_credits_live: int | None
    plan_credits_live: int | None
    rpm_limit: int | None
    max_concurrency: int | None
    cooldown_until: datetime | None
    credentials: list[FirecrawlCredentialResponse] = Field(default_factory=list)


class FirecrawlAccountsResponse(FirecrawlAdminModel):
    accounts: list[FirecrawlAccountResponse]


class FirecrawlJobResponse(FirecrawlAdminModel):
    id: int
    account_id: str | None
    credential_id: str | None
    endpoint: str = Field(pattern=JOB_ENDPOINT_PATTERN)
    upstream_job_id: str | None
    status: str
    estimated_credits_reserved: int | None
    credits_used_final: int | None
    created_at: datetime
    completed_at: datetime | None
    last_polled_at: datetime | None


class FirecrawlJobsResponse(FirecrawlAdminModel):
    jobs: list[FirecrawlJobResponse]


class FirecrawlRequestLogResponse(FirecrawlAdminModel):
    id: int
    account_id: str | None
    credential_id: str | None
    endpoint: str = Field(pattern=REQUEST_LOG_ENDPOINT_PATTERN)
    upstream_job_id: str | None
    status: str
    upstream_status_code: int | None
    estimated_credits_pre: int | None
    credits_used_final: int | None
    latency_ms: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class FirecrawlRequestLogsResponse(FirecrawlAdminModel):
    logs: list[FirecrawlRequestLogResponse]


class FirecrawlAccountsByStatusResponse(FirecrawlAdminModel):
    active: int
    rate_limited: int
    credit_exhausted: int
    paused: int


class FirecrawlRecentRequestsResponse(FirecrawlAdminModel):
    total: int
    success: int
    error: int


class FirecrawlEndpointBreakdownResponse(FirecrawlAdminModel):
    scrape: int
    map: int
    search: int
    crawl: int
    batch_scrape: int


class FirecrawlOverviewResponse(FirecrawlAdminModel):
    total_accounts: int
    active_accounts: int
    total_remaining_credits: int
    total_budget_credits: int
    accounts_by_status: FirecrawlAccountsByStatusResponse
    active_jobs: int
    recent_requests: FirecrawlRecentRequestsResponse
    endpoint_breakdown: FirecrawlEndpointBreakdownResponse


class FirecrawlAccountCreateRequest(FirecrawlAdminModel):
    id: str = Field(min_length=1)
    team_label: str = Field(min_length=1)
    plan_type: str = Field(default="unknown", min_length=1)
    monthly_budget_credits: int | None = Field(default=None, ge=0)
    remaining_credits_live: int | None = Field(default=None, ge=0)
    plan_credits_live: int | None = Field(default=None, ge=0)
    rpm_limit: int | None = Field(default=None, ge=1)
    max_concurrency: int | None = Field(default=None, ge=1)


class FirecrawlAccountUpdateRequest(FirecrawlAdminModel):
    status: str | None = Field(default=None, pattern=ACCOUNT_STATUS_PATTERN)
    monthly_budget_credits: int | None = Field(default=None, ge=0)
    remaining_credits_live: int | None = Field(default=None, ge=0)
    plan_credits_live: int | None = Field(default=None, ge=0)
    rpm_limit: int | None = Field(default=None, ge=1)
    max_concurrency: int | None = Field(default=None, ge=1)
    cooldown_until: datetime | None = None


class FirecrawlCredentialCreateRequest(FirecrawlAdminModel):
    id: str = Field(min_length=1)
    name: str | None = Field(default=None, min_length=1)
    api_key: str = Field(min_length=1)
    status: str = Field(default="active", pattern=CREDENTIAL_STATUS_PATTERN)


class FirecrawlCredentialUpdateRequest(FirecrawlAdminModel):
    status: str = Field(pattern=CREDENTIAL_STATUS_PATTERN)
