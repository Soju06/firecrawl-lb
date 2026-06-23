from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, TypeGuard

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.crypto import TokenEncryptor
from app.db.session import SessionLocal
from app.modules.firecrawl.client import FirecrawlUpstreamResponse, create_firecrawl_client
from app.modules.firecrawl.repository import FirecrawlRepository

logger = logging.getLogger(__name__)


class FirecrawlRefreshClient(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        json: dict[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> FirecrawlUpstreamResponse: ...


@dataclass(frozen=True, slots=True)
class _CreditUsage:
    remaining_credits: int | None
    plan_credits: int | None
    billing_period_start: datetime | None
    billing_period_end: datetime | None


@dataclass(frozen=True, slots=True)
class _QueueStatus:
    active_jobs: int | None
    max_concurrency: int | None


class FirecrawlRefreshService:
    def __init__(self, session: AsyncSession, encryptor: TokenEncryptor | None = None) -> None:
        self._repository = FirecrawlRepository(session, encryptor=encryptor)
        self._encryptor = encryptor or TokenEncryptor()

    async def refresh_once(self, client: FirecrawlRefreshClient | None = None) -> None:
        refresh_client = client or create_firecrawl_client()
        now = datetime.now(UTC).replace(tzinfo=None)
        accounts = await self._repository.list_account_records()
        for account in accounts:
            credential = next((item for item in account.credentials if item.status == "active"), None)
            if credential is None:
                continue
            api_key = self._encryptor.decrypt(credential.api_key_encrypted)
            try:
                usage_response = await refresh_client.request("GET", "/v2/team/credit-usage", api_key=api_key)
                queue_response = await refresh_client.request("GET", "/v2/team/queue-status", api_key=api_key)
                usage = _parse_credit_usage(_require_success_json(usage_response, "credit usage refresh failed"))
                queue = _parse_queue_status(_require_success_json(queue_response, "queue status refresh failed"))
                await self._repository.update_account_refresh_success(
                    account,
                    remaining_credits=usage.remaining_credits,
                    plan_credits=usage.plan_credits,
                    billing_period_start=usage.billing_period_start,
                    billing_period_end=usage.billing_period_end,
                    queue_active_jobs=queue.active_jobs,
                    queue_max_concurrency=queue.max_concurrency,
                    refreshed_at=now,
                )
            except Exception as exc:
                await self._repository.mark_account_refresh_error(account, _safe_error_message(exc), now)
        await self._repository.commit()


class FirecrawlRefreshScheduler:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        interval_seconds: int,
        enabled: bool,
    ) -> None:
        self._session_factory = session_factory
        self._interval_seconds = interval_seconds
        self._enabled = enabled
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not self._enabled or self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                async with self._session_factory() as session:
                    await FirecrawlRefreshService(session).refresh_once()
            except Exception:
                logger.warning("Firecrawl refresh pass failed", exc_info=True)
            await asyncio.sleep(self._interval_seconds)


def build_firecrawl_refresh_scheduler(
    *,
    enabled: bool = False,
    interval_seconds: int = 300,
) -> FirecrawlRefreshScheduler:
    return FirecrawlRefreshScheduler(
        session_factory=SessionLocal,
        interval_seconds=interval_seconds,
        enabled=enabled,
    )


def _require_success_json(response: FirecrawlUpstreamResponse, label: str) -> Mapping[str, object]:
    if response.status < 200 or response.status >= 300:
        raise ValueError(label)
    if response.json_body is None:
        raise ValueError(label)
    return response.json_body


def _parse_credit_usage(payload: Mapping[str, object]) -> _CreditUsage:
    data = _nested_data(payload)
    return _CreditUsage(
        remaining_credits=_int_from_keys(data, ("remaining", "remainingCredits", "remaining_credits")),
        plan_credits=_int_from_keys(data, ("plan", "planCredits", "plan_credits", "totalCredits")),
        billing_period_start=_datetime_from_keys(data, ("billingPeriodStart", "billing_period_start", "periodStart")),
        billing_period_end=_datetime_from_keys(data, ("billingPeriodEnd", "billing_period_end", "periodEnd")),
    )


def _parse_queue_status(payload: Mapping[str, object]) -> _QueueStatus:
    data = _nested_data(payload)
    return _QueueStatus(
        active_jobs=_int_from_keys(data, ("active", "activeJobs", "active_jobs", "queueActiveJobs")),
        max_concurrency=_int_from_keys(data, ("maxConcurrency", "max_concurrency", "concurrency")),
    )


def _nested_data(payload: Mapping[str, object]) -> Mapping[str, object]:
    data = payload.get("data")
    if _is_string_object_mapping(data):
        return data
    return payload


def _int_from_keys(payload: Mapping[str, object], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
    return None


def _datetime_from_keys(payload: Mapping[str, object], keys: tuple[str, ...]) -> datetime | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return _parse_datetime(value)
    return None


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _safe_error_message(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    return message.replace("Bearer ", "").replace("fc-", "[redacted]-")[:500]


def _is_string_object_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    return isinstance(value, Mapping) and all(isinstance(key, str) for key in value)
