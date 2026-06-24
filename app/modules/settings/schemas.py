from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FirecrawlRuntimeSettingsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    refresh_scheduler_enabled: bool
    data_dir: str
    database_url_masked: str
    encryption_key_file: str
