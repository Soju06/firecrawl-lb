from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config.settings import get_settings
from app.core.crypto import TokenEncryptor
from app.db.models import FirecrawlAccountRecord, FirecrawlCredentialRecord, FirecrawlJobRecord
from app.db.session import SessionLocal
from app.main import create_app
from app.modules.firecrawl.client import FirecrawlUpstreamResponse


@dataclass(slots=True)
class _CapturedRequest:
    method: str
    path: str
    api_key: str
    json: dict[str, object] | None


class _FakeFirecrawlClient:
    def __init__(self, responses: list[FirecrawlUpstreamResponse]) -> None:
        self._responses = responses
        self.requests: list[_CapturedRequest] = []

    async def request(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        json: dict[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> FirecrawlUpstreamResponse:
        del params
        self.requests.append(_CapturedRequest(method=method, path=path, api_key=api_key, json=json))
        return self._responses.pop(0)


async def test_refresh_pass_persists_credit_usage_and_queue_status(monkeypatch, db_setup: bool) -> None:
    del db_setup
    from app.modules.firecrawl.refresh import FirecrawlRefreshService

    await _insert_account_with_credential(account_id="account-1", credential_id="credential-1", api_key="fc-refresh")
    fake_client = _FakeFirecrawlClient(
        [
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={
                    "data": {
                        "remaining": 321,
                        "plan": 1000,
                        "billingPeriodStart": "2026-06-01T00:00:00Z",
                        "billingPeriodEnd": "2026-07-01T00:00:00Z",
                    }
                },
                text_body=None,
            ),
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={"active": 2, "maxConcurrency": 8},
                text_body=None,
            ),
        ]
    )

    async with SessionLocal() as session:
        await FirecrawlRefreshService(session).refresh_once(fake_client)

    assert fake_client.requests == [
        _CapturedRequest("GET", "/v2/team/credit-usage", "fc-refresh", None),
        _CapturedRequest("GET", "/v2/team/queue-status", "fc-refresh", None),
    ]

    async with SessionLocal() as session:
        account = await session.get(FirecrawlAccountRecord, "account-1")

    assert account is not None
    assert account.remaining_credits_live == 321
    assert account.plan_credits_live == 1000
    assert account.billing_period_start == datetime(2026, 6, 1, 0, 0)
    assert account.billing_period_end == datetime(2026, 7, 1, 0, 0)
    assert account.queue_active_jobs == 2
    assert account.queue_max_concurrency == 8
    assert account.last_usage_refresh_at is not None
    assert account.last_queue_refresh_at is not None
    assert account.last_refresh_error_at is None
    assert account.last_refresh_error_message is None


async def test_admin_firecrawl_routes_require_overridable_admin_auth(monkeypatch, db_setup: bool) -> None:
    del db_setup
    monkeypatch.setenv("FIRECRAWL_LB_PASSWORD_HASH", "configured")
    get_settings.cache_clear()
    import app.modules.firecrawl.api as firecrawl_api

    app = create_app()
    unauth_transport = ASGITransport(app=app)
    async with AsyncClient(transport=unauth_transport, base_url="http://testserver") as client:
        rejected = await client.get("/v2/admin/firecrawl/accounts")
        public_proxy = await client.post("/v2/scrape", json={"url": "https://example.com"})

    assert rejected.status_code in {401, 403}
    assert public_proxy.status_code != 401
    assert public_proxy.status_code != 403

    assert hasattr(firecrawl_api, "require_firecrawl_admin")
    app.dependency_overrides[firecrawl_api.require_firecrawl_admin] = lambda: None
    auth_transport = ASGITransport(app=app)
    async with AsyncClient(transport=auth_transport, base_url="http://testserver") as client:
        accepted = await client.get("/v2/admin/firecrawl/accounts")

    assert accepted.status_code == 200


async def test_crawl_job_status_uses_original_credential_and_settles_once(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    fake_client = _FakeFirecrawlClient(
        [
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={"success": True, "id": "crawl-upstream-1"},
                text_body=None,
            ),
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={"success": True, "status": "completed", "creditsUsed": 7},
                text_body=None,
            ),
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={"success": True, "status": "completed", "creditsUsed": 7},
                text_body=None,
            ),
        ]
    )
    monkeypatch.setattr("app.modules.firecrawl.api.create_firecrawl_client", lambda: fake_client)
    await _insert_account_with_credential(
        account_id="account-1",
        credential_id="credential-1",
        api_key="fc-original",
        remaining_credits=100,
    )
    await _insert_account_with_credential(
        account_id="account-2",
        credential_id="credential-2",
        api_key="fc-other",
        remaining_credits=10,
    )

    submit = await async_client.post("/v2/crawl", json={"url": "https://example.com"})
    first_poll = await async_client.get("/v2/crawl/crawl-upstream-1")
    second_poll = await async_client.get("/v2/crawl/crawl-upstream-1")

    assert submit.status_code == 200
    assert first_poll.status_code == 200
    assert second_poll.status_code == 200
    assert fake_client.requests == [
        _CapturedRequest("POST", "/v2/crawl", "fc-original", {"url": "https://example.com"}),
        _CapturedRequest("GET", "/v2/crawl/crawl-upstream-1", "fc-original", None),
        _CapturedRequest("GET", "/v2/crawl/crawl-upstream-1", "fc-original", None),
    ]

    async with SessionLocal() as session:
        account = await session.get(FirecrawlAccountRecord, "account-1")
        other = await session.get(FirecrawlAccountRecord, "account-2")
        result = await session.execute(select(FirecrawlJobRecord))
        jobs = result.scalars().all()

    assert account is not None
    assert other is not None
    assert account.remaining_credits_live == 93
    assert other.remaining_credits_live == 10
    assert len(jobs) == 1
    assert jobs[0].account_id == "account-1"
    assert jobs[0].credential_id == "credential-1"
    assert jobs[0].endpoint == "crawl"
    assert jobs[0].upstream_job_id == "crawl-upstream-1"
    assert jobs[0].status == "completed"
    assert jobs[0].credits_used_final == 7


async def test_batch_scrape_cancel_uses_original_credential(async_client: AsyncClient, monkeypatch) -> None:
    fake_client = _FakeFirecrawlClient(
        [
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={"success": True, "jobId": "batch-upstream-1"},
                text_body=None,
            ),
            FirecrawlUpstreamResponse(
                status=200,
                headers={"content-type": "application/json"},
                json_body={"success": True, "status": "cancelled"},
                text_body=None,
            ),
        ]
    )
    monkeypatch.setattr("app.modules.firecrawl.api.create_firecrawl_client", lambda: fake_client)
    await _insert_account_with_credential(account_id="account-1", credential_id="credential-1", api_key="fc-batch")

    submit = await async_client.post("/v2/batch/scrape", json={"urls": ["https://example.com"]})
    cancel = await async_client.delete("/v2/batch/scrape/batch-upstream-1")

    assert submit.status_code == 200
    assert cancel.status_code == 200
    assert fake_client.requests == [
        _CapturedRequest("POST", "/v2/batch/scrape", "fc-batch", {"urls": ["https://example.com"]}),
        _CapturedRequest("DELETE", "/v2/batch/scrape/batch-upstream-1", "fc-batch", None),
    ]


async def test_old_legacy_proxy_routes_are_not_mounted(async_client: AsyncClient) -> None:
    assert (await async_client.get("/v1/models")).status_code == 404
    assert (await async_client.get("/api/oauth/status")).status_code == 404


async def _insert_account_with_credential(
    *,
    account_id: str,
    credential_id: str,
    api_key: str,
    remaining_credits: int = 500,
) -> None:
    encryptor = TokenEncryptor()
    async with SessionLocal() as session:
        session.add(
            FirecrawlAccountRecord(
                id=account_id,
                team_label=account_id,
                plan_type="standard",
                remaining_credits_live=remaining_credits,
                plan_credits_live=1000,
                queue_max_concurrency=10,
            )
        )
        session.add(
            FirecrawlCredentialRecord(
                id=credential_id,
                account_id=account_id,
                name="primary",
                api_key_encrypted=encryptor.encrypt(api_key),
            )
        )
        await session.commit()
