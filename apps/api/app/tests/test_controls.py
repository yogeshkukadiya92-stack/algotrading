from __future__ import annotations

from datetime import time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, BrokerAccount, Order, OrderEvent, RiskProfile, Strategy, SystemControl, User


def create_user(db_session) -> tuple[User, str]:
    user = User(
        email="controls-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Controls User",
        auto_trading_enabled=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, create_access_token(user.id)


def create_paper_setup(db_session, user: User) -> BrokerAccount:
    account = BrokerAccount(
        user_id=user.id,
        broker_name="paper",
        display_name="Paper Broker",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=True,
        is_paper=True,
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
        allow_live_trading=False,
        allow_auto_trading=False,
    )
    db_session.add_all([account, profile])
    db_session.commit()
    db_session.refresh(account)
    return account


def order_payload(account: BrokerAccount, **overrides) -> dict:
    payload = {
        "broker_account_id": account.id,
        "symbol": "RELIANCE",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "quantity": 10,
        "price": "2500",
        "source": "manual",
        "mode": "paper",
        "lot_size": 1,
    }
    payload.update(overrides)
    return payload


def strategy_payload(account: BrokerAccount) -> dict:
    return {
        "name": "DemoStrategy",
        "version": "0.1.0",
        "mode": "paper",
        "broker_account_id": account.id,
        "symbol": "NIFTY",
        "quantity": 1,
        "price": "24800",
        "stop_loss": "24750",
        "target": "24900",
    }


def test_control_status_defaults_to_kill_switch_off(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.get("/controls/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["kill_switch_enabled"] is False
    assert db_session.scalar(select(SystemControl)) is not None


def test_enable_disable_kill_switch_creates_audit_events(client, db_session) -> None:
    user, token = create_user(db_session)

    enable_response = client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Operator emergency stop"},
    )
    disable_response = client.post("/controls/kill-switch/disable", headers={"Authorization": f"Bearer {token}"})

    assert enable_response.status_code == 200
    assert enable_response.json()["kill_switch_enabled"] is True
    assert disable_response.status_code == 200
    assert disable_response.json()["kill_switch_enabled"] is False
    audit_event_types = {
        event.event_type for event in db_session.scalars(select(AuditEvent).where(AuditEvent.user_id == user.id)).all()
    }
    assert "controls.kill_switch_enabled" in audit_event_types
    assert "controls.kill_switch_disabled" in audit_event_types


def test_kill_switch_blocks_new_orders_before_risk_engine(client, db_session, monkeypatch) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)
    client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Circuit breaker"},
    )

    def fail_risk(*_args, **_kwargs):
        raise AssertionError("Risk engine should not run while kill switch is active")

    monkeypatch.setattr("app.services.order_management.order_management_service._evaluate_risk", fail_risk)

    response = client.post("/orders", headers={"Authorization": f"Bearer {token}"}, json=order_payload(account))

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "RISK_REJECTED"
    assert body["risk_status"] == "REJECTED"
    assert body["events"][-1]["event_type"] == "KILL_SWITCH_REJECTED"
    assert "Circuit breaker" in body["events"][-1]["message"]


def test_disabling_kill_switch_allows_manual_paper_orders_again(client, db_session) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)
    client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Temporary halt"},
    )

    blocked_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="blocked_while_kill_switch_on"),
    )
    disable_response = client.post("/controls/kill-switch/disable", headers={"Authorization": f"Bearer {token}"})
    allowed_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="allowed_after_kill_switch_off"),
    )

    assert blocked_response.status_code == 201
    assert blocked_response.json()["order"]["status"] == "RISK_REJECTED"
    assert disable_response.status_code == 200
    assert disable_response.json()["kill_switch_enabled"] is False
    assert allowed_response.status_code == 201
    assert allowed_response.json()["order"]["status"] == "OPEN"
    assert allowed_response.json()["order"]["risk_status"] == "APPROVED"


def test_existing_open_paper_order_can_be_cancelled_with_kill_switch_enabled(client, db_session) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)
    create_response = client.post("/orders", headers={"Authorization": f"Bearer {token}"}, json=order_payload(account))
    order_id = create_response.json()["order"]["id"]
    client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Cancel open risk"},
    )

    cancel_response = client.post(f"/orders/{order_id}/cancel", headers={"Authorization": f"Bearer {token}"})

    assert cancel_response.status_code == 200
    assert cancel_response.json()["order"]["status"] == "CANCELLED"


def test_reset_paper_session_cancels_open_orders_and_audits(client, db_session) -> None:
    user, token = create_user(db_session)
    account = create_paper_setup(db_session, user)
    create_response = client.post("/orders", headers={"Authorization": f"Bearer {token}"}, json=order_payload(account))
    order_id = create_response.json()["order"]["id"]

    response = client.post("/controls/paper-session/reset", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["cancelled_orders"] == 1
    order = db_session.get(Order, order_id)
    assert order.status == "CANCELLED"
    event = db_session.scalar(select(OrderEvent).where(OrderEvent.order_id == order_id, OrderEvent.event_type == "PAPER_SESSION_RESET"))
    assert event is not None
    audit = db_session.scalar(select(AuditEvent).where(AuditEvent.user_id == user.id, AuditEvent.event_type == "controls.paper_session_reset"))
    assert audit is not None


def test_kill_switch_stops_running_strategies(client, db_session) -> None:
    user, token = create_user(db_session)
    strategy = Strategy(
        user_id=user.id,
        name="DemoStrategy",
        version="0.1.0",
        status="RUNNING",
        mode="paper",
        config={},
    )
    db_session.add(strategy)
    db_session.commit()

    response = client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Strategy halt"},
    )

    assert response.status_code == 200
    db_session.refresh(strategy)
    assert strategy.status == "STOPPED"


def test_kill_switch_blocks_strategy_start(client, db_session) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)
    create_response = client.post("/strategies", headers={"Authorization": f"Bearer {token}"}, json=strategy_payload(account))
    strategy_id = create_response.json()["id"]
    client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Strategy start blocked"},
    )

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 400
    assert "Strategy start blocked" in response.json()["detail"]
    assert db_session.scalars(select(Order)).all() == []


def test_dashboard_shows_kill_switch_status() -> None:
    dashboard_path = Path(__file__).resolve().parents[3] / "web" / "app" / "(workspace)" / "dashboard" / "page.tsx"
    source = dashboard_path.read_text()

    assert "fetchControlStatus" in source
    assert "Kill Switch Status" in source
    assert "controlStatus?.kill_switch_enabled" in source
