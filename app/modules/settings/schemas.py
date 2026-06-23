from __future__ import annotations

from app.modules.shared.schemas import DashboardModel


class FirecrawlRuntimeSettingsResponse(DashboardModel):
    refresh_scheduler_enabled: bool
    data_dir: str
    database_url_masked: str
    encryption_key_file: str
