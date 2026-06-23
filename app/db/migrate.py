from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from anyio import to_thread
from sqlalchemy import create_engine

from app.core.config.settings import get_settings
from app.db.migration_url import to_sync_database_url
from app.db.models import Base


@dataclass(frozen=True)
class MigrationState:
    current_revision: str | None
    head_revision: str | None
    has_alembic_version_table: bool
    has_legacy_migrations_table: bool
    needs_upgrade: bool


@dataclass(frozen=True)
class MigrationRunResult:
    current_revision: str | None
    bootstrap: None = None


def _script_location() -> str:
    return str((Path(__file__).resolve().parent / "alembic").resolve())


def _build_alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", _script_location())
    config.set_main_option("sqlalchemy.url", to_sync_database_url(database_url))
    config.attributes["configure_logger"] = False
    return config


def _current_revision(database_url: str) -> str | None:
    engine = create_engine(to_sync_database_url(database_url), future=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            return context.get_current_revision()
    finally:
        engine.dispose()


def get_head_revision() -> str | None:
    script = ScriptDirectory.from_config(_build_alembic_config(get_settings().database_url))
    return script.get_current_head()


def inspect_migration_state(database_url: str):
    current = _current_revision(database_url)
    head = ScriptDirectory.from_config(_build_alembic_config(database_url)).get_current_head()
    return MigrationState(
        current_revision=current,
        head_revision=head,
        has_alembic_version_table=current is not None,
        has_legacy_migrations_table=False,
        needs_upgrade=current != head,
    )


def run_migrations(database_url: str | None = None) -> str | None:
    db_url = database_url or get_settings().database_url
    config = _build_alembic_config(db_url)
    command.upgrade(config, "head")
    return _current_revision(db_url)


async def run_startup_migrations(database_url: str | None = None):
    db_url = database_url or get_settings().database_url
    await to_thread.run_sync(run_migrations, db_url)
    return MigrationRunResult(current_revision=_current_revision(db_url))


def check_schema_drift(database_url: str | None = None) -> tuple[str, ...]:
    db_url = database_url or get_settings().database_url
    engine = create_engine(to_sync_database_url(db_url), future=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "compare_type": True,
                    "target_metadata": Base.metadata,
                    "render_as_batch": connection.dialect.name == "sqlite",
                },
            )
            diffs = compare_metadata(context, Base.metadata)
            return tuple(str(diff) for diff in diffs)
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="firecrawl-lb-db")
    parser.add_argument("--db-url", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database schema to head.")
    upgrade_parser.add_argument("revision", nargs="?", default="head")
    subparsers.add_parser("check", help="Check model/schema drift.")
    args = parser.parse_args()

    db_url = args.db_url or get_settings().database_url
    if args.command == "upgrade":
        config = _build_alembic_config(db_url)
        command.upgrade(config, args.revision)
        return
    if args.command == "check":
        drift = check_schema_drift(db_url)
        if drift:
            for item in drift:
                print(item)
            raise SystemExit(1)
        print("No schema drift detected.")
        return
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
