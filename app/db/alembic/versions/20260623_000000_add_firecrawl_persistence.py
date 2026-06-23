"""initial firecrawl-lb schema

Revision ID: 20260623_firecrawl_base
Revises:
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op

from app.db.models import Base

revision = "20260623_firecrawl_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
