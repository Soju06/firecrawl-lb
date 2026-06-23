from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.firecrawl.models import (
    FirecrawlAccount,
    FirecrawlAccountStatus,
    FirecrawlCredential,
    FirecrawlCredentialStatus,
)
from app.modules.firecrawl.routing import NoFirecrawlAccountAvailable, select_account
from app.modules.firecrawl.usage import estimate_credits


def test_search_credit_estimate_scales_by_limit_sources_and_scrape_options() -> None:
    estimate = estimate_credits(
        "search",
        {
            "limit": 11,
            "sources": ["web", "news"],
            "scrapeOptions": {"formats": ["markdown", "json"], "onlyCleanContent": True},
        },
    )

    assert estimate == 46


def test_scrape_uses_response_credits_when_present() -> None:
    assert estimate_credits("scrape", {"url": "https://example.com"}, response_json={"creditsUsed": 7}) == 7


def test_select_account_groups_same_team_capacity() -> None:
    now = datetime.now(UTC)
    accounts = [
        FirecrawlAccount(
            id="free-a-1",
            team_label="team-a",
            plan_type="free",
            remaining_credits=900,
            plan_credits=1000,
            rpm_used={"scrape": 10},
            credentials=[FirecrawlCredential(id="cred-a-1", api_key="fc-a1")],
        ),
        FirecrawlAccount(
            id="free-a-2",
            team_label="team-a",
            plan_type="free",
            remaining_credits=900,
            plan_credits=1000,
            rpm_used={"scrape": 0},
            credentials=[FirecrawlCredential(id="cred-a-2", api_key="fc-a2")],
        ),
        FirecrawlAccount(
            id="hobby-b",
            team_label="team-b",
            plan_type="hobby",
            remaining_credits=1000,
            plan_credits=5000,
            credentials=[FirecrawlCredential(id="cred-b", api_key="fc-b")],
        ),
    ]

    selected = select_account(accounts, "scrape", {"url": "https://example.com"}, now=now)

    assert selected.account.id == "hobby-b"
    assert selected.credential.id == "cred-b"


def test_select_account_excludes_cooldown_and_credit_exhausted() -> None:
    now = datetime.now(UTC)
    accounts = [
        FirecrawlAccount(
            id="cooldown",
            team_label="team-cooldown",
            plan_type="standard",
            remaining_credits=100000,
            plan_credits=100000,
            cooldown_until=now + timedelta(seconds=30),
            credentials=[FirecrawlCredential(id="cred-cooldown", api_key="fc-c")],
        ),
        FirecrawlAccount(
            id="exhausted",
            team_label="team-exhausted",
            plan_type="standard",
            remaining_credits=0,
            plan_credits=100000,
            status=FirecrawlAccountStatus.CREDIT_EXHAUSTED,
            credentials=[FirecrawlCredential(id="cred-exhausted", api_key="fc-e")],
        ),
    ]

    with pytest.raises(NoFirecrawlAccountAvailable) as exc_info:
        select_account(accounts, "scrape", {"url": "https://example.com"}, now=now)

    assert "cooldown" in str(exc_info.value)
    assert "status=credit_exhausted" in str(exc_info.value)


def test_select_account_excludes_accounts_without_active_credentials() -> None:
    now = datetime.now(UTC)
    accounts = [
        FirecrawlAccount(
            id="invalid-credential",
            team_label="team-invalid",
            plan_type="standard",
            remaining_credits=100000,
            plan_credits=100000,
            credentials=[
                FirecrawlCredential(
                    id="cred-invalid",
                    api_key="fc-invalid",
                    status=FirecrawlCredentialStatus.INVALID,
                )
            ],
        ),
    ]

    with pytest.raises(NoFirecrawlAccountAvailable) as exc_info:
        select_account(accounts, "scrape", {"url": "https://example.com"}, now=now)

    assert "credentials" in str(exc_info.value)


def test_select_account_excludes_same_team_concurrency_saturation() -> None:
    now = datetime.now(UTC)
    accounts = [
        FirecrawlAccount(
            id="team-a-1",
            team_label="team-a",
            plan_type="free",
            remaining_credits=1000,
            plan_credits=1000,
            inflight=2,
            credentials=[FirecrawlCredential(id="cred-a-1", api_key="fc-a1")],
        ),
        FirecrawlAccount(
            id="team-a-2",
            team_label="team-a",
            plan_type="free",
            remaining_credits=1000,
            plan_credits=1000,
            credentials=[FirecrawlCredential(id="cred-a-2", api_key="fc-a2")],
        ),
    ]

    with pytest.raises(NoFirecrawlAccountAvailable) as exc_info:
        select_account(accounts, "scrape", {"url": "https://example.com"}, now=now)

    assert "team_concurrency" in str(exc_info.value)
