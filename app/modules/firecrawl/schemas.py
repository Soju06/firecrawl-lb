from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

ACCOUNT_STATUS_PATTERN = r"^(active|rate_limited|credit_exhausted|paused|invalid)$"
CREDENTIAL_STATUS_PATTERN = r"^(active|paused|invalid)$"


class FirecrawlAdminModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    @field_serializer("cooldown_until", check_fields=False, when_used="json")
    def serialize_datetime_as_utc(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.isoformat() + "Z"
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
