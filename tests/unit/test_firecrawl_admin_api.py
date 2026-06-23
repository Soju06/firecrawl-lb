from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient

from app.core.crypto import TokenEncryptor
from app.db.models import FirecrawlAccountRecord, FirecrawlCredentialRecord
from app.db.session import SessionLocal


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
