from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.sanitization import mask_sensitive_data
from app.models import Alert, AuditEvent, Order, OrderEvent, Signal, Strategy, User


class AlertService:
    def create_alert(
        self,
        db: Session,
        *,
        user_id: str,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        entity_type: str,
        entity_id: str | None,
    ) -> Alert:
        alert = Alert(
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.add(alert)
        return alert

    def list_alerts(
        self,
        db: Session,
        user: User,
        *,
        severity: str | None = None,
        alert_type: str | None = None,
        created_on: date | None = None,
    ) -> list[Alert]:
        query = select(Alert).where(Alert.user_id == user.id)
        if severity:
            query = query.where(Alert.severity == severity.upper())
        if alert_type:
            query = query.where(Alert.alert_type == alert_type)
        if created_on:
            start = datetime.combine(created_on, time.min)
            end = datetime.combine(created_on, time.max)
            query = query.where(Alert.created_at >= start, Alert.created_at <= end)
        return list(db.scalars(query.order_by(Alert.created_at.desc())).all())

    def mark_read(self, db: Session, user: User, alert_id: str) -> Alert:
        alert = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.user_id == user.id))
        if alert is None:
            raise ValueError("Alert not found")
        alert.is_read = True
        db.commit()
        db.refresh(alert)
        return alert

    def list_audit_logs(
        self,
        db: Session,
        user: User,
        *,
        created_on: date | None = None,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).where(AuditEvent.user_id == user.id)
        if event_type:
            query = query.where(AuditEvent.event_type == event_type)
        if created_on:
            start = datetime.combine(created_on, time.min)
            end = datetime.combine(created_on, time.max)
            query = query.where(AuditEvent.created_at >= start, AuditEvent.created_at <= end)
        return list(db.scalars(query.order_by(AuditEvent.created_at.desc())).all())

    def list_order_logs(
        self,
        db: Session,
        user: User,
        *,
        created_on: date | None = None,
        event_type: str | None = None,
        symbol: str | None = None,
    ) -> list[OrderEvent]:
        query = (
            select(OrderEvent)
            .join(Order)
            .where(Order.user_id == user.id)
            .options(selectinload(OrderEvent.order))
        )
        if event_type:
            query = query.where(OrderEvent.event_type == event_type)
        if symbol:
            query = query.where(Order.symbol == symbol.upper())
        if created_on:
            start = datetime.combine(created_on, time.min)
            end = datetime.combine(created_on, time.max)
            query = query.where(OrderEvent.created_at >= start, OrderEvent.created_at <= end)
        return list(db.scalars(query.order_by(OrderEvent.created_at.desc())).all())

    def list_signal_logs(
        self,
        db: Session,
        user: User,
        *,
        created_on: date | None = None,
        event_type: str | None = None,
        symbol: str | None = None,
    ) -> list[Signal]:
        query = select(Signal).where(Signal.user_id == user.id).options(selectinload(Signal.strategy))
        if event_type:
            query = query.where(Signal.status == event_type)
        if symbol:
            query = query.where(Signal.symbol == symbol.upper())
        if created_on:
            start = datetime.combine(created_on, time.min)
            end = datetime.combine(created_on, time.max)
            query = query.where(Signal.created_at >= start, Signal.created_at <= end)
        return list(db.scalars(query.order_by(Signal.created_at.desc())).all())

    def list_system_logs(
        self,
        db: Session,
        user: User,
        *,
        created_on: date | None = None,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        query = select(AuditEvent).where(
            AuditEvent.user_id == user.id,
            AuditEvent.entity_type.in_(("system_control", "market_data", "system")),
        )
        if event_type:
            query = query.where(AuditEvent.event_type == event_type)
        if created_on:
            start = datetime.combine(created_on, time.min)
            end = datetime.combine(created_on, time.max)
            query = query.where(AuditEvent.created_at >= start, AuditEvent.created_at <= end)
        return list(db.scalars(query.order_by(AuditEvent.created_at.desc())).all())

    def sanitize_payload(self, payload: Any) -> Any:
        return mask_sensitive_data(payload)


alert_service = AlertService()
