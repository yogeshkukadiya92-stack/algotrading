from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.alerts import AuditLogResponse, OrderLogResponse, SignalLogResponse, SystemLogResponse
from app.services.alerts import alert_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/audit", response_model=list[AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_filter: date | None = Query(default=None, alias="date"),
    event_type: str | None = None,
) -> list[AuditLogResponse]:
    events = alert_service.list_audit_logs(db, current_user, created_on=date_filter, event_type=event_type)
    return [
        AuditLogResponse(
            id=event.id,
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            message=event.message,
            raw_payload=alert_service.sanitize_payload(event.raw_payload),
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get("/orders", response_model=list[OrderLogResponse])
def list_order_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_filter: date | None = Query(default=None, alias="date"),
    event_type: str | None = None,
    symbol: str | None = None,
) -> list[OrderLogResponse]:
    events = alert_service.list_order_logs(
        db, current_user, created_on=date_filter, event_type=event_type, symbol=symbol
    )
    return [
        OrderLogResponse(
            id=event.id,
            order_id=event.order_id,
            event_type=event.event_type,
            old_status=event.old_status,
            new_status=event.new_status,
            message=event.message,
            raw_payload=alert_service.sanitize_payload(event.raw_payload),
            symbol=event.order.symbol,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get("/signals", response_model=list[SignalLogResponse])
def list_signal_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_filter: date | None = Query(default=None, alias="date"),
    event_type: str | None = None,
    symbol: str | None = None,
) -> list[SignalLogResponse]:
    signals = alert_service.list_signal_logs(
        db, current_user, created_on=date_filter, event_type=event_type, symbol=symbol
    )
    return [
        SignalLogResponse(
            id=signal.id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity,
            status=signal.status,
            reason=signal.reason,
            mode=signal.mode,
            created_at=signal.created_at,
        )
        for signal in signals
    ]


@router.get("/system", response_model=list[SystemLogResponse])
def list_system_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_filter: date | None = Query(default=None, alias="date"),
    event_type: str | None = None,
) -> list[SystemLogResponse]:
    events = alert_service.list_system_logs(db, current_user, created_on=date_filter, event_type=event_type)
    return [
        SystemLogResponse(
            id=event.id,
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            message=event.message,
            raw_payload=alert_service.sanitize_payload(event.raw_payload),
            created_at=event.created_at,
        )
        for event in events
    ]
