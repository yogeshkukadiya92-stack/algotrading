from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Order, PnlSnapshot, Position, RiskProfile, User


@dataclass(frozen=True)
class JobRunResult:
    processed: int
    created: int
    skipped: int
    timestamp: datetime


class DailyPnlSnapshotJob:
    def run(self, db: Session, *, as_of: date | None = None) -> JobRunResult:
        snapshot_date = as_of or date.today()
        users = list(db.scalars(select(User)).all())
        created = 0
        skipped = 0
        for user in users:
            existing = db.scalar(select(PnlSnapshot).where(PnlSnapshot.user_id == user.id, PnlSnapshot.date == snapshot_date))
            if existing is not None:
                skipped += 1
                continue

            realized = db.scalar(
                select(func.coalesce(func.sum(Position.realized_pnl), 0)).where(Position.user_id == user.id)
            ) or Decimal("0")
            unrealized = db.scalar(
                select(func.coalesce(func.sum(Position.unrealized_pnl), 0)).where(Position.user_id == user.id)
            ) or Decimal("0")
            snapshot = PnlSnapshot(
                user_id=user.id,
                date=snapshot_date,
                realized_pnl=Decimal(str(realized)),
                unrealized_pnl=Decimal(str(unrealized)),
                total_pnl=Decimal(str(realized)) + Decimal(str(unrealized)),
            )
            db.add(snapshot)
            db.flush()
            db.add(
                AuditEvent(
                    user_id=user.id,
                    event_type="jobs.daily_pnl_snapshot.created",
                    entity_type="pnl_snapshot",
                    entity_id=snapshot.id,
                    message="Daily P&L snapshot created",
                    raw_payload={"date": snapshot_date.isoformat()},
                )
            )
            created += 1
        db.commit()
        return JobRunResult(processed=len(users), created=created, skipped=skipped, timestamp=datetime.now(UTC))


class AutoSquareOffPlaceholderJob:
    def run(self, db: Session, *, current_time: time | None = None) -> JobRunResult:
        now = current_time or datetime.now().time()
        profiles = list(db.scalars(select(RiskProfile)).all())
        created = 0
        skipped = 0
        for profile in profiles:
            if now < profile.auto_square_off_time:
                skipped += 1
                continue
            db.add(
                AuditEvent(
                    user_id=profile.user_id,
                    event_type="jobs.auto_square_off.placeholder",
                    entity_type="system",
                    entity_id=None,
                    message="Auto square-off placeholder reached",
                    raw_payload={"scheduled_time": profile.auto_square_off_time.isoformat(), "executed": False},
                )
            )
            created += 1
        db.commit()
        return JobRunResult(processed=len(profiles), created=created, skipped=skipped, timestamp=datetime.now(UTC))


daily_pnl_snapshot_job = DailyPnlSnapshotJob()
auto_square_off_placeholder_job = AutoSquareOffPlaceholderJob()
