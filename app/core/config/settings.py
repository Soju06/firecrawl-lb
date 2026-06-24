from __future__ import annotations

import os
from functools import lru_cache
from ipaddress import ip_network
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.auth.dashboard_mode import DashboardAuthMode, normalize_dashboard_auth_proxy_header

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILES = (BASE_DIR / ".env", BASE_DIR / ".env.local")
DOCKER_DATA_DIR = Path("/var/lib/firecrawl-lb")
type StringListInput = str | list[str] | None


def _in_container() -> bool:
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


def _default_home_dir() -> Path:
    env_dir = os.getenv("FIRECRAWL_LB_DATA_DIR")
    if env_dir and env_dir.strip():
        return Path(env_dir.strip())
    home_dir = Path.home() / ".firecrawl-lb"
    if home_dir.exists():
        return home_dir
    if _in_container():
        return DOCKER_DATA_DIR
    return home_dir


def _configured_http_port() -> int:
    raw_env_port = os.getenv("PORT")
    if raw_env_port:
        try:
            port = int(raw_env_port.strip())
        except ValueError:
            return 2465
        if port > 0:
            return port
    return 2465


def _normalize_cidr_list(value: StringListInput, *, field_name: str, invalid_label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cidrs = [entry.strip() for entry in value.split(",") if entry.strip()]
    elif isinstance(value, list):
        cidrs = [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()]
    else:
        raise TypeError(f"{field_name} must be a list or comma-separated string")
    for cidr in cidrs:
        try:
            ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ValueError(f"Invalid {invalid_label}: {cidr}") from exc
    return cidrs


DEFAULT_HOME_DIR = _default_home_dir()
DEFAULT_DB_PATH = DEFAULT_HOME_DIR / "store.db"
DEFAULT_ENCRYPTION_KEY_FILE = DEFAULT_HOME_DIR / "encryption.key"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FIRECRAWL_LB_",
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default_factory=_default_home_dir)
    database_url: str = DEFAULT_DATABASE_URL
    database_pool_size: int = Field(default=15, gt=0)
    database_max_overflow: int = Field(default=10, ge=0)
    database_background_pool_size: int | None = Field(default=None, gt=0)
    database_background_max_overflow: int | None = Field(default=None, ge=0)
    database_pool_timeout_seconds: float = Field(default=30.0, gt=0)
    database_pool_recycle_seconds: int = Field(default=1800, gt=0)
    database_migrate_on_startup: bool = True
    database_sqlite_pre_migrate_backup_enabled: bool = True
    database_sqlite_pre_migrate_backup_max_files: int = Field(default=5, ge=1)
    database_sqlite_startup_check_mode: Literal["quick", "full", "off"] = "quick"
    database_alembic_auto_remap_enabled: bool = False
    database_migrations_fail_fast: bool = True

    encryption_key_file: Path = DEFAULT_ENCRYPTION_KEY_FILE
    usage_refresh_enabled: bool = True
    usage_refresh_interval_seconds: int = Field(default=60, gt=0)

    dashboard_auth_mode: DashboardAuthMode = DashboardAuthMode.STANDARD
    dashboard_auth_proxy_header: str = "Remote-User"
    dashboard_bootstrap_token: str | None = None
    firewall_trust_proxy_headers: bool = False
    firewall_trusted_proxy_cidrs: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["127.0.0.1/32", "::1/128"]
    )
    firewall_ip_cache_ttl_seconds: int = Field(default=30, gt=0)

    metrics_enabled: bool = False
    metrics_port: int = 9090
    log_format: str = "text"
    otel_enabled: bool = False
    otel_exporter_endpoint: str = ""
    leader_election_enabled: bool = False
    leader_election_ttl_seconds: int = 600
    backpressure_max_concurrent_requests: int = 0
    bulkhead_proxy_limit: int = Field(default=512, ge=0)
    bulkhead_proxy_http_limit: int | None = Field(default=None, ge=0)
    bulkhead_dashboard_limit: int = Field(default=50, ge=0)
    memory_warning_threshold_mb: int = 0
    memory_reject_threshold_mb: int = 0
    shutdown_drain_timeout_seconds: int = 30
    http_connector_limit: int = 100
    http_connector_limit_per_host: int = 50
    max_decompressed_body_bytes: int = Field(default=32 * 1024 * 1024, gt=0)
    max_decompressed_responses_body_bytes: int = Field(default=128 * 1024 * 1024, gt=0)

    @field_validator("data_dir", mode="before")
    @classmethod
    def _expand_data_dir(cls, value: str | Path) -> Path:
        if isinstance(value, Path):
            return value.expanduser()
        if isinstance(value, str):
            stripped = value.strip()
            return Path(stripped).expanduser() if stripped else _default_home_dir()
        raise TypeError("data_dir must be a path")

    @field_validator("database_url")
    @classmethod
    def _expand_database_url(cls, value: str) -> str:
        for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
            if value.startswith(prefix):
                path = value[len(prefix) :]
                if path.startswith("~"):
                    return f"{prefix}{Path(path).expanduser()}"
        return value

    @field_validator("encryption_key_file", mode="before")
    @classmethod
    def _expand_encryption_key_file(cls, value: str | Path) -> Path:
        if isinstance(value, Path):
            return value.expanduser()
        if isinstance(value, str):
            return Path(value).expanduser()
        raise TypeError("encryption_key_file must be a path")

    @field_validator("firewall_trusted_proxy_cidrs", mode="before")
    @classmethod
    def _normalize_firewall_trusted_proxy_cidrs(cls, value: StringListInput) -> list[str]:
        return _normalize_cidr_list(
            value,
            field_name="firewall_trusted_proxy_cidrs",
            invalid_label="firewall trusted proxy CIDR",
        )

    @field_validator("dashboard_auth_proxy_header", mode="before")
    @classmethod
    def _normalize_dashboard_auth_proxy_header(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("dashboard_auth_proxy_header must be a string")
        return normalize_dashboard_auth_proxy_header(value)

    @model_validator(mode="after")
    def _apply_data_dir_defaults(self) -> "Settings":
        if self.data_dir == DEFAULT_HOME_DIR:
            return self
        explicitly_set = self.model_fields_set
        if "database_url" not in explicitly_set and self.database_url == DEFAULT_DATABASE_URL:
            self.database_url = f"sqlite+aiosqlite:///{self.data_dir / 'store.db'}"
        if "encryption_key_file" not in explicitly_set and self.encryption_key_file == DEFAULT_ENCRYPTION_KEY_FILE:
            self.encryption_key_file = self.data_dir / "encryption.key"
        return self

    @model_validator(mode="after")
    def _normalize_bulkhead_limits(self) -> "Settings":
        if self.bulkhead_proxy_http_limit is None:
            self.bulkhead_proxy_http_limit = self.bulkhead_proxy_limit
        return self

    @model_validator(mode="after")
    def _validate_metrics_port(self) -> "Settings":
        if self.metrics_port == _configured_http_port():
            raise ValueError(f"metrics_port must not match the main application port ({_configured_http_port()})")
        return self

    @model_validator(mode="after")
    def _validate_dashboard_auth_mode(self) -> "Settings":
        if self.dashboard_auth_mode != DashboardAuthMode.TRUSTED_HEADER:
            return self
        if not self.firewall_trust_proxy_headers:
            raise ValueError("dashboard_auth_mode=trusted_header requires firewall_trust_proxy_headers=true")
        if not self.firewall_trusted_proxy_cidrs:
            raise ValueError("dashboard_auth_mode=trusted_header requires non-empty firewall_trusted_proxy_cidrs")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
