from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Protocol, TypeGuard

from app.core.crypto import TokenEncryptor
from app.db.models import FirecrawlJobRecord, FirecrawlRequestLogRecord
from app.modules.firecrawl.client import FirecrawlUpstreamResponse
from app.modules.firecrawl.repository import FirecrawlRepository
from app.modules.firecrawl.routing import NoFirecrawlAccountAvailable, select_account
from app.modules.firecrawl.usage import estimate_credits


class FirecrawlRequester(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        *,
        api_key: str,
        json: dict[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> FirecrawlUpstreamResponse: ...


class FirecrawlProxyService:
    def __init__(self, repository: FirecrawlRepository, encryptor: TokenEncryptor | None = None) -> None:
        self._repository = repository
        self._encryptor = encryptor or TokenEncryptor()

    async def proxy(
        self,
        endpoint: str,
        payload: dict[str, object],
        client: FirecrawlRequester,
        params: Mapping[str, str] | None = None,
    ) -> FirecrawlUpstreamResponse:
        accounts = await self._repository.list_accounts()
        selected = select_account(accounts, endpoint, payload)
        started = time.perf_counter()
        response = await client.request(
            "POST",
            f"/v2/{endpoint}",
            api_key=selected.credential.api_key,
            json=payload,
            params=params,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        now = datetime.now(UTC)
        credits_used = estimate_credits(endpoint, payload, response.json_body)
        status = _request_status(response.status)
        await self._record_outcome(
            account_id=selected.account.id,
            credential_id=selected.credential.id,
            endpoint=endpoint,
            response=response,
            status=status,
            estimated_credits=selected.estimated_credits,
            credits_used=credits_used,
            latency_ms=latency_ms,
            now=now,
            settle_success=True,
        )
        await self._repository.commit()
        return response

    async def submit_job(
        self,
        endpoint: str,
        path: str,
        payload: dict[str, object],
        client: FirecrawlRequester,
        params: Mapping[str, str] | None = None,
    ) -> FirecrawlUpstreamResponse:
        accounts = await self._repository.list_accounts()
        selected = select_account(accounts, endpoint, payload)
        started = time.perf_counter()
        response = await client.request(
            "POST",
            path,
            api_key=selected.credential.api_key,
            json=payload,
            params=params,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        now = datetime.now(UTC)
        credits_used = estimate_credits(endpoint, payload, response.json_body)
        status = _request_status(response.status)
        upstream_job_id = _upstream_job_id(response.json_body)
        await self._record_outcome(
            account_id=selected.account.id,
            credential_id=selected.credential.id,
            endpoint=endpoint,
            response=response,
            status=status,
            estimated_credits=selected.estimated_credits,
            credits_used=credits_used,
            latency_ms=latency_ms,
            now=now,
            settle_success=False,
        )
        if 200 <= response.status < 300 and upstream_job_id is not None:
            self._repository.add_job_record(
                FirecrawlJobRecord(
                    account_id=selected.account.id,
                    credential_id=selected.credential.id,
                    endpoint=endpoint,
                    upstream_job_id=upstream_job_id,
                    status="submitted",
                    estimated_credits_reserved=selected.estimated_credits,
                )
            )
        await self._repository.commit()
        return response

    async def proxy_job_operation(
        self,
        *,
        endpoint: str,
        upstream_path: str,
        upstream_job_id: str,
        method: str,
        client: FirecrawlRequester,
    ) -> FirecrawlUpstreamResponse | None:
        job = await self._repository.get_job_record(endpoint, upstream_job_id)
        if job is None or job.credential is None:
            return None
        response = await client.request(
            method,
            upstream_path,
            api_key=self._encryptor.decrypt(job.credential.api_key_encrypted),
            json=None,
        )
        now = datetime.now(UTC)
        if method == "GET" and 200 <= response.status < 300:
            status = _job_status(response.json_body)
            credits_used = _credits_used(response.json_body)
            job.status = status or job.status
            job.last_polled_at = now
            if status is not None and _is_terminal_job_status(status) and credits_used is not None:
                await self._repository.settle_job_once(
                    job,
                    status=status,
                    credits_used=credits_used,
                    completed_at=now,
                )
        elif method == "DELETE" and 200 <= response.status < 300:
            job.status = _job_status(response.json_body) or "cancelled"
            job.completed_at = now
        await self._repository.commit()
        return response

    async def _record_outcome(
        self,
        *,
        account_id: str,
        credential_id: str,
        endpoint: str,
        response: FirecrawlUpstreamResponse,
        status: str,
        estimated_credits: int,
        credits_used: int,
        latency_ms: int,
        now: datetime,
        settle_success: bool,
    ) -> None:
        error_message = _error_message(response.json_body, response.text_body)
        await self._repository.record_request(
            FirecrawlRequestLogRecord(
                account_id=account_id,
                credential_id=credential_id,
                endpoint=endpoint,
                upstream_job_id=_upstream_job_id(response.json_body),
                status=status,
                upstream_status_code=response.status,
                estimated_credits_pre=estimated_credits,
                credits_used_final=credits_used,
                latency_ms=latency_ms,
                error_code=status if response.status >= 400 else None,
                error_message=error_message,
            )
        )
        if 200 <= response.status < 300 and settle_success:
            await self._repository.apply_success(account_id, credits_used)
            return
        if response.status == 401:
            await self._repository.mark_credential_invalid(credential_id, error_message, now)
            return
        if response.status == 402:
            await self._repository.mark_account_credit_exhausted(account_id)
            return
        if response.status == 429:
            await self._repository.mark_account_rate_limited(account_id, _cooldown_until(response.headers, now))


def no_account_response(exc: NoFirecrawlAccountAvailable) -> dict[str, str]:
    return {"error": "no_firecrawl_account_available", "message": str(exc)}


def _request_status(upstream_status: int) -> str:
    if 200 <= upstream_status < 300:
        return "success"
    if upstream_status == 401:
        return "credential_invalid"
    if upstream_status == 402:
        return "credit_exhausted"
    if upstream_status == 429:
        return "rate_limited"
    return "error"


def _cooldown_until(headers: Mapping[str, str], now: datetime) -> datetime:
    raw_retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if raw_retry_after is None:
        return now + timedelta(seconds=60)
    try:
        retry_after_seconds = int(raw_retry_after)
    except ValueError:
        return now + timedelta(seconds=60)
    return now + timedelta(seconds=max(0, retry_after_seconds))


def _error_message(json_body: dict[str, object] | None, text_body: str | None) -> str | None:
    if json_body is None:
        return text_body
    message = json_body.get("error")
    if isinstance(message, str):
        return message
    nested_error = json_body.get("error")
    if _is_string_object_mapping(nested_error):
        nested_message = nested_error.get("message")
        if isinstance(nested_message, str):
            return nested_message
    return None


def _upstream_job_id(json_body: dict[str, object] | None) -> str | None:
    if json_body is None:
        return None
    for key in ("id", "jobId"):
        value = json_body.get(key)
        if isinstance(value, str):
            return value
    data = json_body.get("data")
    if _is_string_object_mapping(data):
        value = data.get("id")
        if isinstance(value, str):
            return value
    return None


def _job_status(json_body: dict[str, object] | None) -> str | None:
    if json_body is None:
        return None
    value = json_body.get("status")
    if isinstance(value, str):
        return value
    data = json_body.get("data")
    if _is_string_object_mapping(data):
        nested = data.get("status")
        if isinstance(nested, str):
            return nested
    return None


def _credits_used(json_body: dict[str, object] | None) -> int | None:
    if json_body is None:
        return None
    value = json_body.get("creditsUsed")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    data = json_body.get("data")
    if _is_string_object_mapping(data):
        nested = data.get("creditsUsed")
        if isinstance(nested, bool):
            return None
        if isinstance(nested, int):
            return nested
    return None


def _is_terminal_job_status(status: str) -> bool:
    return status.lower() in {"completed", "complete", "finished", "failed", "cancelled", "canceled"}


def _is_string_object_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    return isinstance(value, Mapping) and all(isinstance(key, str) for key in value)
