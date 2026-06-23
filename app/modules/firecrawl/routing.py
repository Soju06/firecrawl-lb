from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.modules.firecrawl.models import (
    FirecrawlAccount,
    FirecrawlAccountStatus,
    FirecrawlCredential,
    FirecrawlCredentialStatus,
    FirecrawlSelectedAccount,
)
from app.modules.firecrawl.usage import estimate_credits

_ENDPOINT_RPM_BY_PLAN: dict[str, dict[str, int]] = {
    "free": {"scrape": 10, "map": 10, "crawl": 1, "search": 5, "batch_scrape": 1},
    "hobby": {"scrape": 100, "map": 100, "crawl": 15, "search": 50, "batch_scrape": 15},
    "standard": {"scrape": 500, "map": 500, "crawl": 50, "search": 250, "batch_scrape": 50},
    "growth": {"scrape": 5_000, "map": 5_000, "crawl": 250, "search": 2_500, "batch_scrape": 250},
}
_CONCURRENCY_BY_PLAN = {
    "free": 2,
    "hobby": 5,
    "standard": 50,
    "growth": 100,
}
_DEFAULT_RPM_LIMIT = 10
_DEFAULT_CONCURRENCY_LIMIT = 2


class NoFirecrawlAccountAvailable(Exception):
    def __init__(self, endpoint: str, rejections: Mapping[str, str]) -> None:
        self.endpoint = endpoint
        self.rejections = dict(rejections)
        formatted_rejections = ", ".join(f"{account_id}: {reason}" for account_id, reason in self.rejections.items())
        super().__init__(f"No Firecrawl account available for {endpoint}; rejections={{{formatted_rejections}}}")


@dataclass(slots=True)
class _TeamUsage:
    rpm_used_by_endpoint: dict[str, int] = field(default_factory=dict)
    inflight: int = 0
    active_jobs: int = 0


def select_account(
    accounts: Sequence[FirecrawlAccount],
    endpoint: str,
    payload: Mapping[str, Any],
    now: datetime | None = None,
) -> FirecrawlSelectedAccount:
    selection_time = now or datetime.now(UTC)
    estimated_credits = estimate_credits(endpoint, payload)
    team_usage_by_label = _build_team_usage(accounts)

    candidates: list[tuple[float, str, FirecrawlAccount, FirecrawlCredential]] = []
    rejections: dict[str, str] = {}
    for account in accounts:
        credential = _active_credential(account.credentials)
        reason = _rejection_reason(
            account=account,
            credential=credential,
            endpoint=endpoint,
            estimated_credits=estimated_credits,
            team_usage=team_usage_by_label[account.team_label],
            now=selection_time,
        )
        if reason is not None:
            rejections[account.id] = reason
            continue
        assert credential is not None
        candidates.append(
            (
                _score_account(account, endpoint, team_usage_by_label[account.team_label]),
                account.id,
                account,
                credential,
            )
        )

    if not candidates:
        raise NoFirecrawlAccountAvailable(endpoint, rejections)

    _score, _account_id, account, credential = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
    return FirecrawlSelectedAccount(
        account=account,
        credential=credential,
        estimated_credits=estimated_credits,
    )


def _build_team_usage(accounts: Sequence[FirecrawlAccount]) -> dict[str, _TeamUsage]:
    team_usage_by_label: dict[str, _TeamUsage] = {}
    for account in accounts:
        team_usage = team_usage_by_label.setdefault(account.team_label, _TeamUsage())
        team_usage.inflight += account.inflight
        team_usage.active_jobs += account.queue_active_jobs
        for endpoint, used in account.rpm_used.items():
            team_usage.rpm_used_by_endpoint[endpoint] = team_usage.rpm_used_by_endpoint.get(endpoint, 0) + used
    return team_usage_by_label


def _active_credential(credentials: Sequence[FirecrawlCredential]) -> FirecrawlCredential | None:
    for credential in credentials:
        if credential.status == FirecrawlCredentialStatus.ACTIVE:
            return credential
    return None


def _rejection_reason(
    *,
    account: FirecrawlAccount,
    credential: FirecrawlCredential | None,
    endpoint: str,
    estimated_credits: int,
    team_usage: _TeamUsage,
    now: datetime,
) -> str | None:
    if account.status != FirecrawlAccountStatus.ACTIVE:
        return f"status={account.status.value}"
    if account.cooldown_until is not None and account.cooldown_until > now:
        return "cooldown"
    if account.remaining_credits < estimated_credits:
        return "credits"
    if credential is None:
        return "credentials"
    if account.rpm_used.get(endpoint, 0) >= _rpm_limit(account, endpoint):
        return "account_rpm"
    if account.inflight + account.queue_active_jobs >= _concurrency_limit(account):
        return "account_concurrency"
    if team_usage.rpm_used_by_endpoint.get(endpoint, 0) >= _rpm_limit(account, endpoint):
        return "team_rpm"
    if team_usage.inflight + team_usage.active_jobs >= _concurrency_limit(account):
        return "team_concurrency"
    return None


def _score_account(account: FirecrawlAccount, endpoint: str, team_usage: _TeamUsage) -> float:
    budget_ratio = account.remaining_credits / max(1, account.plan_credits)
    rpm_ratio = 1 - (team_usage.rpm_used_by_endpoint.get(endpoint, 0) / max(1, _rpm_limit(account, endpoint)))
    concurrency_ratio = 1 - ((team_usage.inflight + team_usage.active_jobs) / max(1, _concurrency_limit(account)))
    health_ratio = 1 / (1 + max(0, account.recent_error_count))
    return budget_ratio * 0.45 + rpm_ratio * 0.25 + concurrency_ratio * 0.20 + health_ratio * 0.10


def _rpm_limit(account: FirecrawlAccount, endpoint: str) -> int:
    plan_limits = _ENDPOINT_RPM_BY_PLAN.get(account.plan_type)
    if plan_limits is None:
        return _DEFAULT_RPM_LIMIT
    return plan_limits.get(endpoint, _DEFAULT_RPM_LIMIT)


def _concurrency_limit(account: FirecrawlAccount) -> int:
    if account.queue_max_concurrency is not None:
        return account.queue_max_concurrency
    return _CONCURRENCY_BY_PLAN.get(account.plan_type, _DEFAULT_CONCURRENCY_LIMIT)
