from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class FirecrawlAccountRecord(Base):
    __tablename__ = "firecrawl_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    team_label: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    plan_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", server_default=text("'active'"), nullable=False)
    monthly_budget_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remaining_credits_live: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_credits_live: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billing_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    billing_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    queue_active_jobs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_waiting_jobs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_max_concurrency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_usage_refresh_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_queue_refresh_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_refresh_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_refresh_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    credentials: Mapped[list["FirecrawlCredentialRecord"]] = relationship(
        "FirecrawlCredentialRecord",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list["FirecrawlJobRecord"]] = relationship("FirecrawlJobRecord", back_populates="account")
    request_logs: Mapped[list["FirecrawlRequestLogRecord"]] = relationship(
        "FirecrawlRequestLogRecord",
        back_populates="account",
    )


class FirecrawlCredentialRecord(Base):
    __tablename__ = "firecrawl_credentials"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("firecrawl_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", server_default=text("'active'"), nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped[FirecrawlAccountRecord] = relationship("FirecrawlAccountRecord", back_populates="credentials")
    jobs: Mapped[list["FirecrawlJobRecord"]] = relationship("FirecrawlJobRecord", back_populates="credential")
    request_logs: Mapped[list["FirecrawlRequestLogRecord"]] = relationship(
        "FirecrawlRequestLogRecord",
        back_populates="credential",
    )


class FirecrawlJobRecord(Base):
    __tablename__ = "firecrawl_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("firecrawl_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    credential_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("firecrawl_credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    upstream_job_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    estimated_credits_reserved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits_used_final: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped[FirecrawlAccountRecord | None] = relationship("FirecrawlAccountRecord", back_populates="jobs")
    credential: Mapped[FirecrawlCredentialRecord | None] = relationship(
        "FirecrawlCredentialRecord",
        back_populates="jobs",
    )


class FirecrawlRequestLogRecord(Base):
    __tablename__ = "firecrawl_request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("firecrawl_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    credential_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("firecrawl_credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    client_api_key_id: Mapped[str | None] = mapped_column(String, nullable=True)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    upstream_job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    upstream_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_credits_pre: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits_used_final: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped[FirecrawlAccountRecord | None] = relationship(
        "FirecrawlAccountRecord",
        back_populates="request_logs",
    )
    credential: Mapped[FirecrawlCredentialRecord | None] = relationship(
        "FirecrawlCredentialRecord",
        back_populates="request_logs",
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class SchedulerLeader(Base):
    __tablename__ = "scheduler_leader"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    leader_id: Mapped[str] = mapped_column(String(100), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class DashboardSettings(Base):
    __tablename__ = "dashboard_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    dashboard_session_ttl_seconds: Mapped[int] = mapped_column(
        Integer,
        default=43200,
        server_default=text("43200"),
        nullable=False,
    )
    totp_required_on_login: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    bootstrap_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    bootstrap_token_hash: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    api_key_auth_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    totp_last_verified_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ApiFirewallAllowlist(Base):
    __tablename__ = "api_firewall_allowlist"

    ip_address: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class RateLimitAttempt(Base):
    __tablename__ = "rate_limit_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)


class CacheInvalidation(Base):
    __tablename__ = "cache_invalidations"

    namespace: Mapped[str] = mapped_column(String(50), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
