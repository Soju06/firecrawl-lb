from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import TokenEncryptor
from app.db.models import (
    FirecrawlAccountRecord,
    FirecrawlCredentialRecord,
    FirecrawlRequestLogRecord,
)
from app.modules.firecrawl.models import (
    FirecrawlAccount,
    FirecrawlAccountStatus,
    FirecrawlCredential,
    FirecrawlCredentialStatus,
)


class FirecrawlRepository:
    def __init__(self, session: AsyncSession, encryptor: TokenEncryptor | None = None) -> None:
        self._session = session
        self._encryptor = encryptor or TokenEncryptor()

    async def list_accounts(self) -> list[FirecrawlAccount]:
        result = await self._session.execute(select(FirecrawlAccountRecord).order_by(FirecrawlAccountRecord.id))
        records = result.scalars().unique().all()
        accounts: list[FirecrawlAccount] = []
        for record in records:
            await self._session.refresh(record, ["credentials"])
            accounts.append(self._to_domain_account(record))
        return accounts

    async def list_account_records(self) -> list[FirecrawlAccountRecord]:
        result = await self._session.execute(
            select(FirecrawlAccountRecord)
            .options(selectinload(FirecrawlAccountRecord.credentials))
            .order_by(FirecrawlAccountRecord.id)
        )
        return list(result.scalars().unique().all())

    async def get_account_record(self, account_id: str) -> FirecrawlAccountRecord | None:
        result = await self._session.execute(
            select(FirecrawlAccountRecord)
            .options(selectinload(FirecrawlAccountRecord.credentials))
            .where(FirecrawlAccountRecord.id == account_id)
        )
        return result.scalars().unique().one_or_none()

    async def get_credential_record(self, credential_id: str) -> FirecrawlCredentialRecord | None:
        return await self._session.get(FirecrawlCredentialRecord, credential_id)

    def add_account_record(self, account: FirecrawlAccountRecord) -> None:
        self._session.add(account)

    def add_credential_record(self, credential: FirecrawlCredentialRecord) -> None:
        self._session.add(credential)

    async def record_request(
        self,
        log: FirecrawlRequestLogRecord,
    ) -> None:
        self._session.add(log)

    async def apply_success(self, account_id: str, credits_used: int) -> None:
        account = await self._session.get(FirecrawlAccountRecord, account_id)
        if account is None:
            return
        if account.remaining_credits_live is not None:
            account.remaining_credits_live = max(0, account.remaining_credits_live - credits_used)
        if account.status == FirecrawlAccountStatus.RATE_LIMITED.value:
            account.status = FirecrawlAccountStatus.ACTIVE.value
            account.cooldown_until = None

    async def mark_credential_invalid(self, credential_id: str, message: str | None, at: datetime) -> None:
        credential = await self._session.get(FirecrawlCredentialRecord, credential_id)
        if credential is None:
            return
        credential.status = FirecrawlCredentialStatus.INVALID.value
        credential.last_error_at = at
        credential.last_error_message = message

    async def mark_account_credit_exhausted(self, account_id: str) -> None:
        account = await self._session.get(FirecrawlAccountRecord, account_id)
        if account is not None:
            account.status = FirecrawlAccountStatus.CREDIT_EXHAUSTED.value

    async def mark_account_rate_limited(self, account_id: str, cooldown_until: datetime) -> None:
        account = await self._session.get(FirecrawlAccountRecord, account_id)
        if account is None:
            return
        account.status = FirecrawlAccountStatus.RATE_LIMITED.value
        account.cooldown_until = cooldown_until

    async def commit(self) -> None:
        await self._session.commit()

    def _to_domain_account(self, record: FirecrawlAccountRecord) -> FirecrawlAccount:
        credentials = [
            FirecrawlCredential(
                id=credential.id,
                api_key=self._encryptor.decrypt(credential.api_key_encrypted),
                status=FirecrawlCredentialStatus(credential.status),
                name=credential.name,
                last_error_at=credential.last_error_at,
                last_error_message=credential.last_error_message,
            )
            for credential in record.credentials
        ]
        return FirecrawlAccount(
            id=record.id,
            team_label=record.team_label,
            plan_type=record.plan_type,
            remaining_credits=record.remaining_credits_live or 0,
            plan_credits=record.plan_credits_live or record.monthly_budget_credits or 1,
            status=FirecrawlAccountStatus(record.status),
            credentials=credentials,
            cooldown_until=record.cooldown_until,
            queue_active_jobs=record.queue_active_jobs or 0,
            queue_max_concurrency=record.queue_max_concurrency,
        )
