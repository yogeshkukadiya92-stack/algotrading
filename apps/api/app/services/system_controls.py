from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Strategy, SystemControl, User
from app.services.alerts import alert_service


class KillSwitchActiveError(ValueError):
    pass


class SystemControlService:
    def get_or_create_control(self, db: Session, user: User) -> SystemControl:
        control = db.scalar(
            select(SystemControl).where(SystemControl.user_id == user.id).order_by(SystemControl.created_at.desc())
        )
        if control is not None:
            return control

        control = SystemControl(user_id=user.id, kill_switch_enabled=False)
        db.add(control)
        db.flush()
        return control

    def get_status(self, db: Session, user: User) -> SystemControl:
        control = self.get_or_create_control(db, user)
        db.commit()
        db.refresh(control)
        return control

    def enable_kill_switch(self, db: Session, user: User, reason: str) -> SystemControl:
        control = self.get_or_create_control(db, user)
        now = datetime.now(UTC)
        control.kill_switch_enabled = True
        control.reason = reason
        control.enabled_at = now
        control.disabled_at = None

        stopped_strategy_ids = self.stop_running_strategies(db, user)
        db.add(
            AuditEvent(
                user_id=user.id,
                event_type="controls.kill_switch_enabled",
                entity_type="system_control",
                entity_id=control.id,
                message="Kill switch enabled; running strategies stopped",
                raw_payload={"reason": reason, "stopped_strategy_ids": stopped_strategy_ids},
            )
        )
        alert_service.create_alert(
            db,
            user_id=user.id,
            alert_type="kill_switch_enabled",
            severity="CRITICAL",
            title="Kill switch enabled",
            message=reason,
            entity_type="system_control",
            entity_id=control.id,
        )
        db.commit()
        db.refresh(control)
        return control

    def disable_kill_switch(self, db: Session, user: User) -> SystemControl:
        control = self.get_or_create_control(db, user)
        control.kill_switch_enabled = False
        control.disabled_at = datetime.now(UTC)
        db.add(
            AuditEvent(
                user_id=user.id,
                event_type="controls.kill_switch_disabled",
                entity_type="system_control",
                entity_id=control.id,
                message="Kill switch disabled",
                raw_payload={},
            )
        )
        db.commit()
        db.refresh(control)
        return control

    def stop_running_strategies(self, db: Session, user: User) -> list[str]:
        strategies = db.scalars(
            select(Strategy).where(Strategy.user_id == user.id, Strategy.status == "RUNNING")
        ).all()
        stopped_ids: list[str] = []
        for strategy in strategies:
            strategy.status = "STOPPED"
            stopped_ids.append(strategy.id)
            db.add(
                AuditEvent(
                    user_id=user.id,
                    event_type="strategy.stopped_by_kill_switch",
                    entity_type="strategy",
                    entity_id=strategy.id,
                    message="Strategy stopped by kill switch",
                    raw_payload={},
                )
            )
            alert_service.create_alert(
                db,
                user_id=user.id,
                alert_type="strategy_stopped",
                severity="WARN",
                title="Strategy stopped by kill switch",
                message=f"{strategy.name} stopped by kill switch.",
                entity_type="strategy",
                entity_id=strategy.id,
            )
        return stopped_ids

    def ensure_orders_allowed(self, db: Session, user: User) -> None:
        control = self.get_or_create_control(db, user)
        if control.kill_switch_enabled:
            reason = control.reason or "New orders are blocked."
            raise KillSwitchActiveError(f"Kill switch is enabled. {reason}")

    def ensure_strategies_allowed(self, db: Session, user: User) -> None:
        control = self.get_or_create_control(db, user)
        if control.kill_switch_enabled:
            self.stop_running_strategies(db, user)
            db.add(
                AuditEvent(
                    user_id=user.id,
                    event_type="strategy.start_blocked_by_kill_switch",
                    entity_type="system_control",
                    entity_id=control.id,
                    message="Strategy start blocked by kill switch",
                    raw_payload={"reason": control.reason},
                )
            )
            db.commit()
            reason = control.reason or "Strategies are stopped."
            raise KillSwitchActiveError(f"Kill switch is enabled. {reason}")


system_control_service = SystemControlService()
