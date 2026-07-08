from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KillSwitchRequest(BaseModel):
    reason: str = Field(default="Emergency stop requested", min_length=3, max_length=500)


class SystemControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    kill_switch_enabled: bool
    reason: str | None
    enabled_at: datetime | None
    disabled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ControlStatusResponse(BaseModel):
    kill_switch_enabled: bool
    reason: str | None
    enabled_at: datetime | None
    disabled_at: datetime | None
