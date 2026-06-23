from __future__ import annotations

from app.db.models import DashboardSettings
from app.modules.settings.repository import SettingsRepository


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def get_settings(self) -> DashboardSettings:
        return await self._repository.get_or_create()
