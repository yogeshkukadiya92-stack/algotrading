from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    entity_type: str
    entity_id: str | None
    is_read: bool
    created_at: datetime


class AuditLogResponse(BaseModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str | None
    message: str
    raw_payload: dict
    created_at: datetime


class OrderLogResponse(BaseModel):
    id: str
    order_id: str
    event_type: str
    old_status: str | None
    new_status: str | None
    message: str
    raw_payload: dict
    symbol: str
    created_at: datetime


class SignalLogResponse(BaseModel):
    id: str
    strategy_id: str
    symbol: str
    side: str
    quantity: int
    status: str
    reason: str
    mode: str
    created_at: datetime


class SystemLogResponse(BaseModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str | None
    message: str
    raw_payload: dict
    created_at: datetime
