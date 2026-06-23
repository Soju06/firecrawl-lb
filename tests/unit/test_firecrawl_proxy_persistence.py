from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import inspect, select

from app.core.crypto import TokenEncryptor
from app.db.models import (
    Base,
    FirecrawlAccountRecord,
    FirecrawlCredentialRecord,
    FirecrawlRequestLogRecord,
)
from app.db.session import SessionLocal, engine


def test_settings_prefers_firecrawl_lb_env_prefix(monkeypatch, tmp_path: Path) -> None:
    # Given: Firecrawl-prefixed environment values.
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'firecrawl.db'}"
    monkeypatch.setenv("FIRECRAWL_LB_DATABASE_URL", database_url)
    monkeypatch.setenv("FIRECRAWL_LB_DATA_DIR", str(tmp_path / "data"))

    from app.core.config.settings import Settings, get_settings

    get_settings.cache_clear()

    # When: settings are loaded.
    settings = Settings()

    # Then: the primary Firecrawl env prefix supplies configuration.
    assert settings.database_url == database_url
    assert settings.data_dir == tmp_path / "data"


async def test_metadata_creates_firecrawl_tables(db_setup: bool) -> None:
    # Given: the test database schema is reset by the autouse fixture.
    assert db_setup is True
    expected_tables = {
        "firecrawl_accounts",
        "firecrawl_credentials",
        "firecrawl_jobs",
        "firecrawl_request_logs",
    }

    # When: SQLAlchemy metadata is inspected.
    async with engine.begin() as conn:
        table_names = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))

    # Then: Firecrawl tables are present in metadata-created schema.
    assert expected_tables <= table_names
    assert expected_tables <= set(Base.metadata.tables)


@dataclass(slots=True)
class _CapturedRequest:
    method: str
    path: str
    api_key: str
    json: dict[str, object] | None


class _FakeFirecrawlClient:
    def __init__(self, status: int, headers: dict[str, str], body: dict[str, object]) -> None:
        self.status = status
        self.headers = headers
        self.body = body
        self.requests: list[_CapturedRequest] = []

    async def request(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        json: dict[str, object] | None = None,
        params: dict[str, str] | None = None,
    ):
        del params
        self.requests.append(_CapturedRequest(method=method, path=path, api_key=api_key, json=json))
        from app.modules.firecrawl.client import FirecrawlUpstreamResponse

        return FirecrawlUpstreamResponse(status=self.status, headers=self.headers, json_body=self.body, text_body=None)


async def test_scrape_proxy_forwards_with_encrypted_credential_and_logs(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    # Given: an active Firecrawl account and encrypted credential.
    fake_client = _FakeFirecrawlClient(200, {"content-type": "application/json"}, {"success": True, "creditsUsed": 3})
    monkeypatch.setattr("app.modules.firecrawl.api.create_firecrawl_client", lambda: fake_client)
    await _insert_account_with_credential(remaining_credits=100)

    # When: the client calls the local scrape proxy.
    response = await async_client.post("/v2/scrape", json={"url": "https://example.com", "formats": ["markdown"]})

    # Then: upstream response is passed through and no plaintext key leaks into the client response or request log.
    assert response.status_code == 200
    assert response.json() == {"success": True, "creditsUsed": 3}
    assert fake_client.requests == [
        _CapturedRequest(
            method="POST",
            path="/v2/scrape",
            api_key="fc-secret",
            json={"url": "https://example.com", "formats": ["markdown"]},
        )
    ]
    assert "fc-secret" not in response.text

    async with SessionLocal() as session:
        account = await session.get(FirecrawlAccountRecord, "account-1")
        result = await session.execute(select(FirecrawlRequestLogRecord))
        logs = result.scalars().all()

    assert account is not None
    assert account.remaining_credits_live == 97
    assert len(logs) == 1
    assert logs[0].account_id == "account-1"
    assert logs[0].credential_id == "credential-1"
    assert logs[0].endpoint == "scrape"
    assert logs[0].status == "success"
    assert logs[0].credits_used_final == 3
    assert logs[0].error_message is None


async def test_rate_limit_marks_account_and_sets_cooldown(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    # Given: upstream returns a Firecrawl rate limit with Retry-After.
    fake_client = _FakeFirecrawlClient(
        429,
        {"content-type": "application/json", "retry-after": "120"},
        {"error": "rate limited"},
    )
    monkeypatch.setattr("app.modules.firecrawl.api.create_firecrawl_client", lambda: fake_client)
    await _insert_account_with_credential(remaining_credits=100)

    # When: the client calls the local scrape proxy.
    response = await async_client.post("/v2/scrape", json={"url": "https://example.com"})

    # Then: the account is locally cooled down and the upstream body/status pass through.
    assert response.status_code == 429
    assert response.json() == {"error": "rate limited"}

    async with SessionLocal() as session:
        account = await session.get(FirecrawlAccountRecord, "account-1")
        result = await session.execute(select(FirecrawlRequestLogRecord))
        logs = result.scalars().all()

    assert account is not None
    assert account.status == "rate_limited"
    assert account.cooldown_until is not None
    assert logs[0].status == "rate_limited"
    assert logs[0].upstream_status_code == 429


async def _insert_account_with_credential(*, remaining_credits: int) -> None:
    encryptor = TokenEncryptor()
    async with SessionLocal() as session:
        session.add(
            FirecrawlAccountRecord(
                id="account-1",
                team_label="team-one",
                plan_type="standard",
                remaining_credits_live=remaining_credits,
                plan_credits_live=100,
            )
        )
        session.add(
            FirecrawlCredentialRecord(
                id="credential-1",
                account_id="account-1",
                name="primary",
                api_key_encrypted=encryptor.encrypt("fc-secret"),
            )
        )
        await session.commit()
