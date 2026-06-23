"""add firecrawl persistence tables

Revision ID: 20260623_000000_add_firecrawl_persistence
Revises: 20260604_000000_add_reauth_required_account_status
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "20260623_000000_add_firecrawl_persistence"
down_revision = "20260604_000000_add_reauth_required_account_status"
branch_labels = None
depends_on = None


def _has_table(connection: Connection, table_name: str) -> bool:
    return sa.inspect(connection).has_table(table_name)


def _indexes(connection: Connection, table_name: str) -> set[str]:
    if not _has_table(connection, table_name):
        return set()
    return {name for index in sa.inspect(connection).get_indexes(table_name) if (name := index["name"]) is not None}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "firecrawl_accounts"):
        op.create_table(
            "firecrawl_accounts",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("team_label", sa.String(), nullable=False),
            sa.Column("plan_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), server_default=sa.text("'active'"), nullable=False),
            sa.Column("monthly_budget_credits", sa.Integer(), nullable=True),
            sa.Column("remaining_credits_live", sa.Integer(), nullable=True),
            sa.Column("plan_credits_live", sa.Integer(), nullable=True),
            sa.Column("billing_period_start", sa.DateTime(), nullable=True),
            sa.Column("billing_period_end", sa.DateTime(), nullable=True),
            sa.Column("queue_active_jobs", sa.Integer(), nullable=True),
            sa.Column("queue_waiting_jobs", sa.Integer(), nullable=True),
            sa.Column("queue_max_concurrency", sa.Integer(), nullable=True),
            sa.Column("cooldown_until", sa.DateTime(), nullable=True),
            sa.Column("last_usage_refresh_at", sa.DateTime(), nullable=True),
            sa.Column("last_queue_refresh_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "ix_firecrawl_accounts_team_label" not in _indexes(bind, "firecrawl_accounts"):
        op.create_index(
            "ix_firecrawl_accounts_team_label",
            "firecrawl_accounts",
            ["team_label"],
            unique=True,
        )
    if not _has_table(bind, "firecrawl_credentials"):
        op.create_table(
            "firecrawl_credentials",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("account_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=False),
            sa.Column("status", sa.String(), server_default=sa.text("'active'"), nullable=False),
            sa.Column("last_validated_at", sa.DateTime(), nullable=True),
            sa.Column("last_error_at", sa.DateTime(), nullable=True),
            sa.Column("last_error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["firecrawl_accounts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_table(bind, "firecrawl_jobs"):
        op.create_table(
            "firecrawl_jobs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("account_id", sa.String(), nullable=True),
            sa.Column("credential_id", sa.String(), nullable=True),
            sa.Column("endpoint", sa.String(), nullable=False),
            sa.Column("upstream_job_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("estimated_credits_reserved", sa.Integer(), nullable=True),
            sa.Column("credits_used_final", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("last_polled_at", sa.DateTime(), nullable=True),
            sa.Column("next_url", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["account_id"], ["firecrawl_accounts.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["credential_id"], ["firecrawl_credentials.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if "ix_firecrawl_jobs_upstream_job_id" not in _indexes(bind, "firecrawl_jobs"):
        op.create_index("ix_firecrawl_jobs_upstream_job_id", "firecrawl_jobs", ["upstream_job_id"])
    if not _has_table(bind, "firecrawl_request_logs"):
        op.create_table(
            "firecrawl_request_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("account_id", sa.String(), nullable=True),
            sa.Column("credential_id", sa.String(), nullable=True),
            sa.Column("client_api_key_id", sa.String(), nullable=True),
            sa.Column("endpoint", sa.String(), nullable=False),
            sa.Column("upstream_job_id", sa.String(), nullable=True),
            sa.Column("requested_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("upstream_status_code", sa.Integer(), nullable=True),
            sa.Column("estimated_credits_pre", sa.Integer(), nullable=True),
            sa.Column("credits_used_final", sa.Integer(), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("error_code", sa.String(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["account_id"], ["firecrawl_accounts.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["credential_id"], ["firecrawl_credentials.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "firecrawl_request_logs"):
        op.drop_table("firecrawl_request_logs")
    if _has_table(bind, "firecrawl_jobs"):
        if "ix_firecrawl_jobs_upstream_job_id" in _indexes(bind, "firecrawl_jobs"):
            op.drop_index("ix_firecrawl_jobs_upstream_job_id", table_name="firecrawl_jobs")
        op.drop_table("firecrawl_jobs")
    if _has_table(bind, "firecrawl_credentials"):
        op.drop_table("firecrawl_credentials")
    if _has_table(bind, "firecrawl_accounts"):
        if "ix_firecrawl_accounts_team_label" in _indexes(bind, "firecrawl_accounts"):
            op.drop_index("ix_firecrawl_accounts_team_label", table_name="firecrawl_accounts")
        op.drop_table("firecrawl_accounts")
