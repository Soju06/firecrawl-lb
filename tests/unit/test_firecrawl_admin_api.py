from __future__ import annotations

from datetime import UTC, datetime

import pytest_asyncio
from httpx import AsyncClient

from app.core.crypto import TokenEncryptor
from app.db.models import (
    FirecrawlAccountRecord,
    FirecrawlCredentialRecord,
    FirecrawlJobRecord,
    FirecrawlRequestLogRecord,
)
from app.db.session import SessionLocal
from app.modules.firecrawl import api as firecrawl_api


@pytest_asyncio.fixture(autouse=True)
async def _allow_firecrawl_admin(app_instance):
    app_instance.dependency_overrides[firecrawl_api.require_firecrawl_admin] = lambda: None
    yield
    app_instance.dependency_overrides.pop(firecrawl_api.require_firecrawl_admin, None)


async def test_admin_creates_lists_and_redacts_firecrawl_credentials(async_client: AsyncClient) -> None:
    # Given: an operator has a plaintext Firecrawl API key.
    plaintext_api_key = "fc-admin-secret"

    # When: the operator creates an account and adds a credential through the admin API.
    account_response = await async_client.post(
        "/v2/admin/firecrawl/accounts",
        json={
            "id": "fc-account-1",
            "team_label": "team one",
            "monthly_budget_credits": 1000,
            "remaining_credits_live": 900,
            "plan_credits_live": 1000,
            "rpm_limit": 60,
            "max_concurrency": 3,
        },
    )
    credential_response = await async_client.post(
        "/v2/admin/firecrawl/accounts/fc-account-1/credentials",
        json={"id": "fc-credential-1", "name": "primary", "api_key": plaintext_api_key},
    )
    list_response = await async_client.get("/v2/admin/firecrawl/accounts")
    detail_response = await async_client.get("/v2/admin/firecrawl/accounts/fc-account-1")

    # Then: the API exposes operational fields and never returns plaintext or encrypted key material.
    assert account_response.status_code == 201
    assert credential_response.status_code == 201
    assert list_response.status_code == 200
    assert detail_response.status_code == 200

    account_payload = account_response.json()
    assert account_payload["plan_type"] == "unknown"
    assert account_payload["rpm_limit"] == 60
    assert account_payload["max_concurrency"] == 3

    credential_payload = credential_response.json()
    assert credential_payload == {"id": "fc-credential-1", "name": "primary", "status": "active"}

    list_text = list_response.text
    detail_text = detail_response.text
    assert plaintext_api_key not in list_text
    assert plaintext_api_key not in detail_text
    assert "api_key" not in list_text
    assert "api_key" not in detail_text
    assert "api_key_encrypted" not in list_text
    assert "api_key_encrypted" not in detail_text

    listed = list_response.json()
    assert listed == {
        "accounts": [
            {
                "id": "fc-account-1",
                "team_label": "team one",
                "plan_type": "unknown",
                "status": "active",
                "monthly_budget_credits": 1000,
                "remaining_credits_live": 900,
                "plan_credits_live": 1000,
                "rpm_limit": 60,
                "max_concurrency": 3,
                "cooldown_until": None,
                "credentials": [{"id": "fc-credential-1", "name": "primary", "status": "active"}],
            }
        ]
    }

    async with SessionLocal() as session:
        credential = await session.get(FirecrawlCredentialRecord, "fc-credential-1")

    assert credential is not None
    assert credential.api_key_encrypted != plaintext_api_key.encode()
    assert TokenEncryptor().decrypt(credential.api_key_encrypted) == plaintext_api_key


async def test_admin_updates_account_and_marks_credential_invalid(async_client: AsyncClient) -> None:
    # Given: a configured Firecrawl account with one active credential.
    await _insert_account_with_credential()
    cooldown_until = datetime(2026, 6, 23, 12, 30, tzinfo=UTC)

    # When: the operator updates routing fields and marks the credential invalid.
    account_response = await async_client.patch(
        "/v2/admin/firecrawl/accounts/fc-account-1",
        json={
            "status": "rate_limited",
            "monthly_budget_credits": 2000,
            "remaining_credits_live": 1500,
            "plan_credits_live": 2000,
            "rpm_limit": 120,
            "max_concurrency": 5,
            "cooldown_until": cooldown_until.isoformat().replace("+00:00", "Z"),
        },
    )
    credential_response = await async_client.patch(
        "/v2/admin/firecrawl/accounts/fc-account-1/credentials/fc-credential-1",
        json={"status": "invalid"},
    )

    # Then: the account and credential responses reflect the operational changes without secrets.
    assert account_response.status_code == 200
    assert credential_response.status_code == 200
    assert "fc-admin-secret" not in account_response.text
    assert "fc-admin-secret" not in credential_response.text
    assert account_response.json()["status"] == "rate_limited"
    assert account_response.json()["cooldown_until"] == "2026-06-23T12:30:00Z"
    assert account_response.json()["rpm_limit"] == 120
    assert account_response.json()["max_concurrency"] == 5
    assert credential_response.json() == {"id": "fc-credential-1", "name": "primary", "status": "invalid"}


async def test_admin_returns_clean_errors_for_missing_and_duplicate_records(async_client: AsyncClient) -> None:
    # Given: one existing Firecrawl account and credential.
    await _insert_account_with_credential()

    # When: the operator targets missing records and duplicates existing IDs.
    missing_account = await async_client.get("/v2/admin/firecrawl/accounts/missing")
    missing_credential = await async_client.patch(
        "/v2/admin/firecrawl/accounts/fc-account-1/credentials/missing",
        json={"status": "paused"},
    )
    duplicate_account = await async_client.post(
        "/v2/admin/firecrawl/accounts",
        json={"id": "fc-account-1", "team_label": "duplicate team"},
    )
    duplicate_credential = await async_client.post(
        "/v2/admin/firecrawl/accounts/fc-account-1/credentials",
        json={"id": "fc-credential-1", "api_key": "fc-other-secret"},
    )

    # Then: the API returns explicit HTTP errors instead of raw database stack traces.
    assert missing_account.status_code == 404
    assert missing_account.json()["detail"] == "Firecrawl account not found"
    assert missing_credential.status_code == 404
    assert missing_credential.json()["detail"] == "Firecrawl credential not found"
    assert duplicate_account.status_code == 409
    assert duplicate_account.json()["detail"] == "Firecrawl account already exists"
    assert duplicate_credential.status_code == 409
    assert duplicate_credential.json()["detail"] == "Firecrawl credential already exists"
    assert "Traceback" not in duplicate_account.text
    assert "Traceback" not in duplicate_credential.text


async def test_admin_lists_jobs_with_filters_ordered_by_created_at(async_client: AsyncClient) -> None:
    # Given: persisted crawl and batch scrape jobs for different accounts.
    await _insert_account_with_credential()
    async with SessionLocal() as session:
        session.add_all(
            [
                FirecrawlJobRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="crawl",
                    upstream_job_id="crawl-old",
                    status="completed",
                    estimated_credits_reserved=3,
                    credits_used_final=2,
                    created_at=datetime(2026, 6, 23, 10, 0),
                    completed_at=datetime(2026, 6, 23, 10, 5),
                    last_polled_at=datetime(2026, 6, 23, 10, 5),
                ),
                FirecrawlJobRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="crawl",
                    upstream_job_id="crawl-new",
                    status="submitted",
                    estimated_credits_reserved=4,
                    created_at=datetime(2026, 6, 23, 11, 0),
                ),
                FirecrawlJobRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="batch_scrape",
                    upstream_job_id="batch-1",
                    status="failed",
                    created_at=datetime(2026, 6, 23, 12, 0),
                ),
            ]
        )
        await session.commit()

    # When: the operator filters for crawl jobs.
    response = await async_client.get("/v2/admin/firecrawl/jobs?endpoint=crawl&limit=10&offset=0")

    # Then: only matching jobs are returned newest first.
    assert response.status_code == 200
    assert response.json() == {
        "jobs": [
            {
                "id": 2,
                "account_id": "fc-account-1",
                "credential_id": "fc-credential-1",
                "endpoint": "crawl",
                "upstream_job_id": "crawl-new",
                "status": "submitted",
                "estimated_credits_reserved": 4,
                "credits_used_final": None,
                "created_at": "2026-06-23T11:00:00",
                "completed_at": None,
                "last_polled_at": None,
            },
            {
                "id": 1,
                "account_id": "fc-account-1",
                "credential_id": "fc-credential-1",
                "endpoint": "crawl",
                "upstream_job_id": "crawl-old",
                "status": "completed",
                "estimated_credits_reserved": 3,
                "credits_used_final": 2,
                "created_at": "2026-06-23T10:00:00",
                "completed_at": "2026-06-23T10:05:00",
                "last_polled_at": "2026-06-23T10:05:00",
            },
        ]
    }


async def test_admin_lists_request_logs_with_filters_ordered_by_created_at(async_client: AsyncClient) -> None:
    # Given: persisted sync request logs across endpoints and statuses.
    await _insert_account_with_credential()
    async with SessionLocal() as session:
        session.add_all(
            [
                FirecrawlRequestLogRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="scrape",
                    upstream_job_id="scrape-1",
                    requested_at=datetime(2026, 6, 23, 9, 0),
                    status="success",
                    upstream_status_code=200,
                    estimated_credits_pre=1,
                    credits_used_final=1,
                    latency_ms=123,
                ),
                FirecrawlRequestLogRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="scrape",
                    requested_at=datetime(2026, 6, 23, 10, 0),
                    status="error",
                    upstream_status_code=500,
                    estimated_credits_pre=1,
                    latency_ms=456,
                    error_code="upstream_error",
                    error_message="Upstream failed",
                ),
                FirecrawlRequestLogRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="map",
                    requested_at=datetime(2026, 6, 23, 11, 0),
                    status="success",
                ),
            ]
        )
        await session.commit()

    # When: the operator filters for scrape logs.
    response = await async_client.get("/v2/admin/firecrawl/logs?endpoint=scrape&limit=10&offset=0")

    # Then: only matching logs are returned newest first using the public created_at field.
    assert response.status_code == 200
    assert response.json() == {
        "logs": [
            {
                "id": 2,
                "account_id": "fc-account-1",
                "credential_id": "fc-credential-1",
                "endpoint": "scrape",
                "upstream_job_id": None,
                "status": "error",
                "upstream_status_code": 500,
                "estimated_credits_pre": 1,
                "credits_used_final": None,
                "latency_ms": 456,
                "error_code": "upstream_error",
                "error_message": "Upstream failed",
                "created_at": "2026-06-23T10:00:00",
            },
            {
                "id": 1,
                "account_id": "fc-account-1",
                "credential_id": "fc-credential-1",
                "endpoint": "scrape",
                "upstream_job_id": "scrape-1",
                "status": "success",
                "upstream_status_code": 200,
                "estimated_credits_pre": 1,
                "credits_used_final": 1,
                "latency_ms": 123,
                "error_code": None,
                "error_message": None,
                "created_at": "2026-06-23T09:00:00",
            },
        ]
    }


async def test_admin_overview_aggregates_firecrawl_state(async_client: AsyncClient) -> None:
    # Given: accounts, active jobs, and recent request logs exist.
    await _insert_account_with_credential()
    async with SessionLocal() as session:
        session.add(
            FirecrawlAccountRecord(
                id="fc-account-2",
                team_label="team two",
                plan_type="standard",
                status="paused",
                monthly_budget_credits=200,
                remaining_credits_live=50,
            )
        )
        session.add_all(
            [
                FirecrawlJobRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="crawl",
                    upstream_job_id="crawl-active",
                    status="submitted",
                    created_at=datetime(2026, 6, 23, 10, 0),
                ),
                FirecrawlJobRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="batch_scrape",
                    upstream_job_id="batch-complete",
                    status="completed",
                    created_at=datetime(2026, 6, 23, 9, 0),
                ),
                FirecrawlRequestLogRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="scrape",
                    requested_at=datetime(2026, 6, 23, 8, 0),
                    status="success",
                ),
                FirecrawlRequestLogRecord(
                    account_id="fc-account-1",
                    credential_id="fc-credential-1",
                    endpoint="search",
                    requested_at=datetime(2026, 6, 23, 8, 1),
                    status="error",
                ),
            ]
        )
        await session.commit()

    # When: the operator requests the Firecrawl overview.
    response = await async_client.get("/v2/admin/firecrawl/overview")

    # Then: aggregate values cover accounts, active jobs, requests, and endpoint counts.
    assert response.status_code == 200
    assert response.json() == {
        "total_accounts": 2,
        "active_accounts": 1,
        "total_remaining_credits": 950,
        "total_budget_credits": 1200,
        "accounts_by_status": {"active": 1, "rate_limited": 0, "credit_exhausted": 0, "paused": 1},
        "active_jobs": 1,
        "recent_requests": {"total": 2, "success": 1, "error": 1},
        "endpoint_breakdown": {"scrape": 1, "map": 0, "search": 1, "crawl": 1, "batch_scrape": 1},
    }


async def _insert_account_with_credential() -> None:
    encryptor = TokenEncryptor()
    async with SessionLocal() as session:
        session.add(
            FirecrawlAccountRecord(
                id="fc-account-1",
                team_label="team one",
                plan_type="standard",
                remaining_credits_live=900,
                plan_credits_live=1000,
            )
        )
        session.add(
            FirecrawlCredentialRecord(
                id="fc-credential-1",
                account_id="fc-account-1",
                name="primary",
                api_key_encrypted=encryptor.encrypt("fc-admin-secret"),
            )
        )
        await session.commit()
