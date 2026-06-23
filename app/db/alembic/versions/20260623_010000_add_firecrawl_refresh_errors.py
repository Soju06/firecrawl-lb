"""add firecrawl refresh error fields

Revision ID: 20260623_firecrawl_refresh
Revises: 20260623_firecrawl_base
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "20260623_firecrawl_refresh"
down_revision = "20260623_firecrawl_base"
branch_labels = None
depends_on = None


def _columns(connection: Connection, table_name: str) -> set[str]:
    if not sa.inspect(connection).has_table(table_name):
        return set()
    return {column["name"] for column in sa.inspect(connection).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "firecrawl_accounts")
    if "last_refresh_error_at" not in columns:
        op.add_column("firecrawl_accounts", sa.Column("last_refresh_error_at", sa.DateTime(), nullable=True))
    if "last_refresh_error_message" not in columns:
        op.add_column("firecrawl_accounts", sa.Column("last_refresh_error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "firecrawl_accounts")
    if "last_refresh_error_message" in columns:
        op.drop_column("firecrawl_accounts", "last_refresh_error_message")
    if "last_refresh_error_at" in columns:
        op.drop_column("firecrawl_accounts", "last_refresh_error_at")
