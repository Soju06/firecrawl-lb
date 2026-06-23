from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.core.crypto import TokenEncryptor
from app.db.models import FirecrawlAccountRecord, FirecrawlCredentialRecord
from app.modules.firecrawl.repository import FirecrawlRepository
from app.modules.firecrawl.schemas import (
    FirecrawlAccountCreateRequest,
    FirecrawlAccountResponse,
    FirecrawlAccountsResponse,
    FirecrawlAccountUpdateRequest,
    FirecrawlCredentialCreateRequest,
    FirecrawlCredentialResponse,
    FirecrawlCredentialUpdateRequest,
)


class FirecrawlAccountNotFoundError(Exception):
    pass


class FirecrawlCredentialNotFoundError(Exception):
    pass


class FirecrawlAccountConflictError(Exception):
    pass


class FirecrawlCredentialConflictError(Exception):
    pass


class FirecrawlAdminService:
    def __init__(self, repository: FirecrawlRepository, encryptor: TokenEncryptor | None = None) -> None:
        self._repository = repository
        self._encryptor = encryptor or TokenEncryptor()

    async def list_accounts(self) -> FirecrawlAccountsResponse:
        accounts = await self._repository.list_account_records()
        return FirecrawlAccountsResponse(accounts=[_account_response(account) for account in accounts])

    async def get_account(self, account_id: str) -> FirecrawlAccountResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        return _account_response(account)

    async def create_account(self, payload: FirecrawlAccountCreateRequest) -> FirecrawlAccountResponse:
        existing = await self._repository.get_account_record(payload.id)
        if existing is not None:
            raise FirecrawlAccountConflictError
        account = FirecrawlAccountRecord(
            id=payload.id,
            team_label=payload.team_label,
            plan_type=payload.plan_type,
            monthly_budget_credits=payload.monthly_budget_credits,
            remaining_credits_live=payload.remaining_credits_live,
            plan_credits_live=payload.plan_credits_live,
            rpm_limit=payload.rpm_limit,
            queue_max_concurrency=payload.max_concurrency,
        )
        self._repository.add_account_record(account)
        try:
            await self._repository.commit()
        except IntegrityError as exc:
            raise FirecrawlAccountConflictError from exc
        return _account_response(account)

    async def update_account(self, account_id: str, payload: FirecrawlAccountUpdateRequest) -> FirecrawlAccountResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if field_name == "max_concurrency":
                account.queue_max_concurrency = value
                continue
            setattr(account, field_name, value)
        await self._repository.commit()
        return _account_response(account)

    async def create_credential(
        self,
        account_id: str,
        payload: FirecrawlCredentialCreateRequest,
    ) -> FirecrawlCredentialResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        existing = await self._repository.get_credential_record(payload.id)
        if existing is not None:
            raise FirecrawlCredentialConflictError
        credential = FirecrawlCredentialRecord(
            id=payload.id,
            account_id=account_id,
            name=payload.name,
            api_key_encrypted=self._encryptor.encrypt(payload.api_key),
            status=payload.status,
        )
        self._repository.add_credential_record(credential)
        try:
            await self._repository.commit()
        except IntegrityError as exc:
            raise FirecrawlCredentialConflictError from exc
        return _credential_response(credential)

    async def update_credential(
        self,
        account_id: str,
        credential_id: str,
        payload: FirecrawlCredentialUpdateRequest,
    ) -> FirecrawlCredentialResponse:
        account = await self._repository.get_account_record(account_id)
        if account is None:
            raise FirecrawlAccountNotFoundError
        credential = await self._repository.get_credential_record(credential_id)
        if credential is None or credential.account_id != account_id:
            raise FirecrawlCredentialNotFoundError
        credential.status = payload.status
        await self._repository.commit()
        return _credential_response(credential)


def _account_response(account: FirecrawlAccountRecord) -> FirecrawlAccountResponse:
    credentials = [] if "credentials" in inspect(account).unloaded else account.credentials
    return FirecrawlAccountResponse(
        id=account.id,
        team_label=account.team_label,
        plan_type=account.plan_type,
        status=account.status,
        monthly_budget_credits=account.monthly_budget_credits,
        remaining_credits_live=account.remaining_credits_live,
        plan_credits_live=account.plan_credits_live,
        rpm_limit=account.rpm_limit,
        max_concurrency=account.queue_max_concurrency,
        cooldown_until=account.cooldown_until,
        credentials=[_credential_response(credential) for credential in credentials],
    )


def _credential_response(credential: FirecrawlCredentialRecord) -> FirecrawlCredentialResponse:
    return FirecrawlCredentialResponse(
        id=credential.id,
        name=credential.name,
        status=credential.status,
    )
