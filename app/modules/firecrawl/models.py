from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FirecrawlAccountStatus(StrEnum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    CREDIT_EXHAUSTED = "credit_exhausted"
    PAUSED = "paused"
    INVALID = "invalid"


class FirecrawlCredentialStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    INVALID = "invalid"


@dataclass(slots=True)
class FirecrawlCredential:
    id: str
    api_key: str
    status: FirecrawlCredentialStatus = FirecrawlCredentialStatus.ACTIVE
    name: str | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None


@dataclass(slots=True)
class FirecrawlAccount:
    id: str
    team_label: str
    plan_type: str
    remaining_credits: int
    plan_credits: int
    status: FirecrawlAccountStatus = FirecrawlAccountStatus.ACTIVE
    credentials: list[FirecrawlCredential] = field(default_factory=list)
    cooldown_until: datetime | None = None
    inflight: int = 0
    rpm_used: dict[str, int] = field(default_factory=dict)
    queue_active_jobs: int = 0
    queue_max_concurrency: int | None = None
    recent_error_count: int = 0


@dataclass(frozen=True, slots=True)
class FirecrawlSelectedAccount:
    account: FirecrawlAccount
    credential: FirecrawlCredential
    estimated_credits: int
