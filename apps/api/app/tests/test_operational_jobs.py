from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from sqlalchemy import select

from app.models import AuditEvent, BrokerAccount, PnlSnapshot, Position, RiskProfile, User
from app.services.operational_jobs import auto_square_off_placeholder_job, daily_pnl_snapshot_job


def _seed_user_state(db_session) -> tuple[User, BrokerAccount]:
    user = User(
        email="jobs@tradepilot.in",
        hashed_password="hash",
        full_name="Jobs User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    account = BrokerAccount(
        user_id=user.id,
        broker_name="paper",
        display_name="Paper Jobs",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=True,
    )
    profile = RiskProfile(
        user_id=user.id,
        max_daily_loss=Decimal("5000"),
        max_order_value=Decimal("100000"),
        max_lots_per_order=20,
        max_trades_per_day=20,
        max_open_positions=20,
        allowed_start_time=time(0, 0),
        allowed_end_time=time(23, 59),
        auto_square_off_time=time(15, 25),
    )
    db_session.add_all([account, profile])
    db_session.commit()
    db_session.refresh(account)
    return user, account


def test_daily_pnl_snapshot_job_creates_snapshot_and_audit_event(db_session) -> None:
    user, account = _seed_user_state(db_session)
    db_session.add(
        Position(
            user_id=user.id,
            broker_account_id=account.id,
            symbol="RELIANCE",
            quantity=1,
            average_price=Decimal("2500"),
            ltp=Decimal("2520"),
            realized_pnl=Decimal("75"),
            unrealized_pnl=Decimal("20"),
            product_type="MIS",
        )
    )
    db_session.commit()

    result = daily_pnl_snapshot_job.run(db_session, as_of=date(2026, 7, 8))

    assert result.created == 1
    snapshot = db_session.scalar(select(PnlSnapshot).where(PnlSnapshot.user_id == user.id))
    assert snapshot is not None
    assert snapshot.realized_pnl == Decimal("75")
    assert snapshot.unrealized_pnl == Decimal("20")
    assert snapshot.total_pnl == Decimal("95")
    audit_event = db_session.scalar(
        select(AuditEvent).where(AuditEvent.event_type == "jobs.daily_pnl_snapshot.created")
    )
    assert audit_event is not None


def test_auto_square_off_placeholder_job_creates_audit_event_after_cutoff(db_session) -> None:
    user, _account = _seed_user_state(db_session)

    result = auto_square_off_placeholder_job.run(db_session, current_time=time(15, 30))

    assert result.created == 1
    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.user_id == user.id,
            AuditEvent.event_type == "jobs.auto_square_off.placeholder",
        )
    )
    assert audit_event is not None
    assert audit_event.raw_payload["executed"] is False
