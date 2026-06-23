from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="firecrawl-lb-tests-"))
TEST_DB_PATH = TEST_DB_DIR / "firecrawl-lb.db"

os.environ["FIRECRAWL_LB_DATABASE_URL"] = os.environ.get(
    "FIRECRAWL_LB_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH}"
)
os.environ["FIRECRAWL_LB_UPSTREAM_BASE_URL"] = "https://example.invalid/backend-api"
os.environ["FIRECRAWL_LB_USAGE_REFRESH_ENABLED"] = "false"
os.environ["FIRECRAWL_LB_MODEL_REGISTRY_ENABLED"] = "false"

from app.db.models import Base  # noqa: E402
from app.db.session import close_db, engine  # noqa: E402
from app.main import create_app  # noqa: E402


def _drop_test_migration_tables(sync_conn) -> None:
    sync_conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    sync_conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))


def _reset_test_database(sync_conn) -> None:
    _drop_test_migration_tables(sync_conn)
    Base.metadata.drop_all(sync_conn)
    Base.metadata.create_all(sync_conn)


@pytest_asyncio.fixture
async def _reset_db_state():
    await close_db()
    async with engine.begin() as conn:
        await conn.run_sync(_reset_test_database)
    return True


@pytest_asyncio.fixture
async def app_instance(_reset_db_state, monkeypatch):
    del _reset_db_state
    import app.main as main_module

    async def _noop_init_db() -> None:
        return None

    monkeypatch.setattr(main_module, "init_db", _noop_init_db)
    return create_app()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def dispose_engine():
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_setup(_reset_db_state):
    del _reset_db_state
    return True


@pytest_asyncio.fixture
async def async_client(app_instance):
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


@pytest.fixture(autouse=True)
def temp_key_file(monkeypatch):
    key_path = TEST_DB_DIR / f"encryption-{uuid4().hex}.key"
    monkeypatch.setenv("FIRECRAWL_LB_ENCRYPTION_KEY_FILE", str(key_path))
    from app.core.config.settings import get_settings

    get_settings.cache_clear()
    return key_path


@pytest.fixture(autouse=True)
def _reset_runtime_caches():
    try:
        from app.core.middleware.firewall_cache import get_firewall_ip_cache

        get_firewall_ip_cache().invalidate_all()
    except Exception:
        pass
    yield
    try:
        from app.core.middleware.firewall_cache import get_firewall_ip_cache

        get_firewall_ip_cache().invalidate_all()
    except Exception:
        pass
