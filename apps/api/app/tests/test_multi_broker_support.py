from __future__ import annotations

from datetime import time
from decimal import Decimal

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, BrokerAccount, RiskProfile, User
from app.services.broker_readonly import broker_readonly_service


def create_user(db_session) -> tuple[User, str]:
    user = User(
        email="multi-broker-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Multi Broker User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

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
    db_session.add(profile)
    db_session.commit()
    return user, create_access_token(user.id)


def create_broker_account(
    db_session,
    user: User,
    *,
    broker_name: str,
    display_name: str,
) -> BrokerAccount:
    account = BrokerAccount(
        user_id=user.id,
        broker_name=broker_name,
        display_name=display_name,
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_user_can_have_multiple_broker_accounts(client, db_session) -> None:
    _user, token = create_user(db_session)

    first = client.post(
        "/brokers/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"broker_name": "zerodha", "display_name": "Zerodha Read Only"},
    )
    second = client.post(
        "/brokers/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"broker_name": "upstox", "display_name": "Upstox Read Only"},
    )
    listed = client.get("/brokers", headers={"Authorization": f"Bearer {token}"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    assert {account["broker_name"] for account in body} == {"zerodha", "upstox"}


def test_orders_return_broker_name_for_selected_account(client, db_session) -> None:
    user, token = create_user(db_session)
    account = create_broker_account(db_session, user, broker_name="upstox", display_name="Upstox Paper View")

    create_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "broker_account_id": account.id,
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "segment": "EQ",
            "transaction_type": "BUY",
            "product_type": "MIS",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": "2500",
            "source": "manual",
            "mode": "paper",
            "lot_size": 1,
        },
    )
    list_response = client.get("/orders", headers={"Authorization": f"Bearer {token}"})

    assert create_response.status_code == 201
    assert create_response.json()["order"]["broker_name"] == "upstox"
    assert list_response.status_code == 200
    assert list_response.json()[0]["broker_name"] == "upstox"


def test_broker_secret_fields_are_redacted_in_audit_payloads(db_session) -> None:
    user, _token = create_user(db_session)
    broker_readonly_service.audit(
        db_session,
        user_id=user.id,
        event_type="broker.secret_check",
        broker_account_id="account_123",
        message="Testing redaction",
        payload={
            "api_key": "should-not-leak",
            "access_token": "should-not-leak",
            "headers": {"Authorization": "Bearer should-not-leak"},
            "nested": {"secret_value": "should-not-leak"},
        },
    )
    db_session.commit()

    event = db_session.scalar(select(AuditEvent).where(AuditEvent.event_type == "broker.secret_check"))

    assert event is not None
    assert event.raw_payload["api_key"] == "***redacted***"
    assert event.raw_payload["access_token"] == "***redacted***"
    assert event.raw_payload["headers"]["Authorization"] == "***redacted***"
    assert event.raw_payload["nested"]["secret_value"] == "***redacted***"
