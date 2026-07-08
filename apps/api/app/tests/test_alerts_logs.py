from __future__ import annotations

from datetime import time
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, BrokerAccount, RiskProfile, User
from app.services.broker_readonly import broker_readonly_service
from app.services.order_management import order_management_service


class FailingBrokerHttpClient:
    def __init__(self, _base_url: str) -> None:
        pass

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        raise RuntimeError("simulated broker outage with token=secret")


@pytest.fixture(autouse=True)
def reset_paper_adapter_state():
    order_management_service.paper_adapter._orders.clear()
    order_management_service.paper_adapter._positions.clear()
    order_management_service.paper_adapter._quotes.clear()
    yield
    order_management_service.paper_adapter._orders.clear()
    order_management_service.paper_adapter._positions.clear()
    order_management_service.paper_adapter._quotes.clear()


def create_user(db_session) -> tuple[User, str]:
    user = User(
        email="alerts-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Alerts User",
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
        max_order_value=Decimal("100"),
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


def create_broker_setup(db_session, user: User) -> BrokerAccount:
    account = BrokerAccount(
        user_id=user.id,
        broker_name="zerodha",
        display_name="Zerodha Read Only",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=False,
        is_paper=False,
    )
    db_session.add(account)
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


def test_risk_rejection_creates_alert_and_can_be_marked_read(client, db_session) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)

    order_response = client.post("/orders", headers={"Authorization": f"Bearer {token}"}, json=order_payload(account))
    alerts_response = client.get("/alerts", headers={"Authorization": f"Bearer {token}"})

    assert order_response.status_code == 201
    assert alerts_response.status_code == 200
    alert = alerts_response.json()[0]
    assert alert["alert_type"] == "risk_rejection"
    assert alert["severity"] == "BLOCK"
    assert alert["is_read"] is False

    read_response = client.post(f"/alerts/{alert['id']}/read", headers={"Authorization": f"Bearer {token}"})

    assert read_response.status_code == 200
    assert read_response.json()["is_read"] is True


def test_filled_order_creates_alert(client, db_session) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)
    account_risk = db_session.scalar(select(RiskProfile).where(RiskProfile.user_id == _user.id))
    account_risk.max_order_value = Decimal("100000")
    db_session.commit()
    order_management_service.paper_adapter.update_market_data(
        "RELIANCE",
        ltp=Decimal("2495"),
        bid_price=Decimal("2494"),
        ask_price=Decimal("2495"),
    )

    response = client.post("/orders", headers={"Authorization": f"Bearer {token}"}, json=order_payload(account))
    alerts_response = client.get("/alerts?alert_type=order_filled", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 201
    assert response.json()["order"]["status"] == "FILLED"
    assert alerts_response.status_code == 200
    assert alerts_response.json()[0]["title"] == "Order filled"


def test_kill_switch_creates_critical_alert(client, db_session) -> None:
    _user, token = create_user(db_session)

    client.post(
        "/controls/kill-switch/enable",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Operator emergency stop"},
    )
    response = client.get("/alerts?severity=CRITICAL", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()[0]["alert_type"] == "kill_switch_enabled"


def test_broker_error_creates_alert(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FailingBrokerHttpClient)
    _user, token = create_user(db_session)
    account = create_broker_setup(db_session, _user)

    broker_response = client.get(f"/brokers/{account.id}/profile", headers={"Authorization": f"Bearer {token}"})
    alerts_response = client.get("/alerts?alert_type=broker_connection_error", headers={"Authorization": f"Bearer {token}"})

    assert broker_response.status_code == 502
    assert alerts_response.status_code == 200
    assert alerts_response.json()[0]["severity"] == "WARN"


def test_market_data_disconnected_creates_alert(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.post("/alerts/market-data-disconnected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["alert_type"] == "market_data_disconnected"
    assert response.json()["severity"] == "WARN"


def test_log_endpoints_return_audit_and_order_logs(client, db_session) -> None:
    _user, token = create_user(db_session)
    account = create_paper_setup(db_session, _user)
    client.post("/orders", headers={"Authorization": f"Bearer {token}"}, json=order_payload(account))

    audit_response = client.get("/logs/audit?event_type=order.risk_rejected", headers={"Authorization": f"Bearer {token}"})
    orders_response = client.get("/logs/orders?symbol=RELIANCE", headers={"Authorization": f"Bearer {token}"})

    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "order.risk_rejected"
    assert orders_response.status_code == 200
    assert any(row["event_type"] == "RISK_REJECTED" for row in orders_response.json())


def test_logs_mask_broker_tokens_and_api_keys(client, db_session) -> None:
    user, token = create_user(db_session)
    db_session.add(
        AuditEvent(
            user_id=user.id,
            event_type="broker.http.request",
            entity_type="broker_account",
            entity_id="broker_001",
            message="Broker request",
            raw_payload={
                "api_key": "real-api-key",
                "access_token": "real-token",
                "headers": {"Authorization": "Bearer real-token"},
                "safe": "visible",
            },
        )
    )
    db_session.commit()

    response = client.get("/logs/audit?event_type=broker.http.request", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()[0]["raw_payload"]
    assert payload["api_key"] == "***redacted***"
    assert payload["access_token"] == "***redacted***"
    assert payload["headers"]["Authorization"] == "***redacted***"
    assert payload["safe"] == "visible"


def test_notification_bell_shows_unread_count() -> None:
    top_bar_path = Path(__file__).resolve().parents[3] / "web" / "components" / "app" / "top-bar.tsx"
    source = top_bar_path.read_text()

    assert "fetchAlerts" in source
    assert "filter((alert) => !alert.is_read).length" in source
    assert "{unreadAlerts}" in source
    assert 'href="/alerts"' in source
