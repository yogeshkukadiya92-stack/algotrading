from datetime import time
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, BrokerAccount, Order, OrderEvent, RiskProfile, User
from app.services.broker_readonly import broker_readonly_service
from app.services.order_management import order_management_service


class LiveOrderHttpClient:
    post_calls = 0

    def __init__(self, _base_url: str) -> None:
        pass

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        return {}

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        type(self).post_calls += 1
        return {"data": {"order_id": "zerodha_live_order_1", "status": "OPEN", "status_message": "accepted"}}


@pytest.fixture(autouse=True)
def reset_paper_adapter() -> None:
    order_management_service.paper_adapter._orders.clear()
    order_management_service.paper_adapter._positions.clear()
    order_management_service.paper_adapter._quotes.clear()


def create_authenticated_user(
    db_session,
    *,
    email: str = "orders-user@tradepilot.in",
    live_trading_enabled: bool = False,
    auto_trading_enabled: bool = False,
) -> tuple[User, str]:
    user = User(
        email=email,
        hashed_password=hash_password("StrongPass123"),
        full_name="Orders User",
        live_trading_enabled=live_trading_enabled,
        auto_trading_enabled=auto_trading_enabled,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, create_access_token(user.id)


def create_broker_account(db_session, user: User, *, static_ip_verified: bool = True) -> BrokerAccount:
    account = BrokerAccount(
        user_id=user.id,
        broker_name="paper",
        display_name="Paper Broker",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=static_ip_verified,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def create_live_broker_account(db_session, user: User, *, static_ip_verified: bool = True) -> BrokerAccount:
    account = BrokerAccount(
        user_id=user.id,
        broker_name="zerodha",
        display_name="Zerodha Live Manual",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=static_ip_verified,
        is_paper=False,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def create_risk_profile(db_session, user: User, **overrides) -> RiskProfile:
    payload = {
        "user_id": user.id,
        "max_daily_loss": Decimal("5000"),
        "max_order_value": Decimal("100000"),
        "max_lots_per_order": 20,
        "max_trades_per_day": 20,
        "max_open_positions": 20,
        "allowed_start_time": time(0, 0),
        "allowed_end_time": time(23, 59),
        "auto_square_off_time": time(15, 25),
        "allow_live_trading": False,
        "allow_auto_trading": False,
    }
    payload.update(overrides)
    profile = RiskProfile(**payload)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


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


def test_create_order_generates_correlation_id_and_routes_to_paper(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["correlation_id"].startswith("corr_")
    assert body["status"] == "OPEN"
    assert body["risk_status"] == "APPROVED"
    assert body["broker_order_id"].startswith("paper_")
    assert [event["event_type"] for event in body["events"]] == [
        "CREATED",
        "RISK_APPROVED",
        "BROKER_RESPONSE",
    ]

    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == body["id"])).all()
    assert {event.event_type for event in audit_events} >= {
        "order.request_received",
        "order.risk_approved",
        "order.broker_response",
    }


def test_create_order_rejects_when_risk_engine_blocks(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, order_type="MARKET", price=None),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "RISK_REJECTED"
    assert body["risk_status"] == "REJECTED"
    assert body["broker_order_id"] is None
    assert body["events"][-1]["event_type"] == "RISK_REJECTED"

    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == body["id"])).all()
    assert any(event.event_type == "order.risk_rejected" for event in audit_events)


def test_list_orders_includes_risk_rejection_reason(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user, max_order_value=Decimal("100"))

    create_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, quantity=10, price="2500"),
    )
    assert create_response.status_code == 201

    response = client.get("/orders", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    rejected_order = response.json()[0]
    assert rejected_order["status"] == "RISK_REJECTED"
    assert rejected_order["events"][-1]["event_type"] == "RISK_REJECTED"
    assert "configured maximum order value" in rejected_order["events"][-1]["message"]


def test_risk_rejected_order_is_not_sent_to_adapter(client, db_session, monkeypatch) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    def fail_place_order(_order):
        raise AssertionError("Risk rejected order should not be sent to paper adapter")

    monkeypatch.setattr(order_management_service.paper_adapter, "place_order", fail_place_order)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, order_type="MARKET", price=None),
    )

    assert response.status_code == 201
    assert response.json()["order"]["status"] == "RISK_REJECTED"
    assert len(order_management_service.paper_adapter._orders) == 0


def test_risk_approved_paper_order_is_sent_to_paper_adapter(client, db_session, monkeypatch) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)
    original_place_order = order_management_service.paper_adapter.place_order
    calls = []

    def spy_place_order(order):
        calls.append(order)
        return original_place_order(order)

    monkeypatch.setattr(order_management_service.paper_adapter, "place_order", spy_place_order)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="paper_adapter_called_001"),
    )

    assert response.status_code == 201
    assert response.json()["order"]["risk_status"] == "APPROVED"
    assert len(calls) == 1
    assert calls[0].correlation_id == "paper_adapter_called_001"
    assert len(order_management_service.paper_adapter._orders) == 1


def test_order_event_is_created_for_each_state_change(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="state_events_001"),
    )

    assert response.status_code == 201
    order_id = response.json()["order"]["id"]
    events = db_session.scalars(
        select(OrderEvent).where(OrderEvent.order_id == order_id).order_by(OrderEvent.created_at)
    ).all()
    assert [(event.old_status, event.new_status, event.event_type) for event in events] == [
        (None, "CREATED", "CREATED"),
        ("CREATED", "RISK_APPROVED", "RISK_APPROVED"),
        ("RISK_APPROVED", "OPEN", "BROKER_RESPONSE"),
    ]


def test_audit_event_is_created_for_order_request(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="audit_request_001"),
    )

    assert response.status_code == 201
    order_id = response.json()["order"]["id"]
    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == order_id,
            AuditEvent.event_type == "order.request_received",
        )
    )
    assert audit_event is not None
    assert audit_event.raw_payload["correlation_id"] == "audit_request_001"


def test_duplicate_correlation_id_is_rejected(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    first_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="duplicate_corr_001"),
    )
    duplicate_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="duplicate_corr_001"),
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    duplicate_body = duplicate_response.json()
    assert duplicate_body["detail"] == "Duplicate correlation_id rejected"
    assert duplicate_body["error_code"] == "http_409"

    orders = db_session.scalars(select(Order).where(Order.correlation_id == "duplicate_corr_001")).all()
    assert len(orders) == 1
    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.event_type == "order.duplicate_rejected",
            AuditEvent.entity_id == orders[0].id,
        )
    )
    assert audit_event is not None


def test_idempotency_key_returns_same_order_for_repeat_request(client, db_session) -> None:
    user, token = create_authenticated_user(db_session, email="idempotency@tradepilot.in")
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idem_order_001",
    }
    first = client.post("/orders", headers=headers, json=order_payload(account, correlation_id="idem_corr_001"))
    second = client.post("/orders", headers=headers, json=order_payload(account, correlation_id="idem_corr_999"))

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["order"]["id"] == second.json()["order"]["id"]
    assert first.json()["order"]["correlation_id"] == second.json()["order"]["correlation_id"]


def test_idempotency_key_conflict_is_rejected_for_different_payload(client, db_session) -> None:
    user, token = create_authenticated_user(db_session, email="idempotency-conflict@tradepilot.in")
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "idem_conflict_001",
    }
    first = client.post("/orders", headers=headers, json=order_payload(account, correlation_id="idem_conflict_a"))
    second = client.post(
        "/orders",
        headers=headers,
        json=order_payload(account, correlation_id="idem_conflict_b", quantity=11),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Idempotency key already used for a different order request"


def test_duplicate_order_request_is_rejected_without_matching_correlation_id(client, db_session) -> None:
    user, token = create_authenticated_user(db_session, email="duplicate-order@tradepilot.in")
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)

    first = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="dup_request_a"),
    )
    second = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="dup_request_b"),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Duplicate order request rejected"


def test_live_order_is_blocked_after_risk_approval_when_global_live_is_disabled(client, db_session) -> None:
    user, token = create_authenticated_user(db_session, live_trading_enabled=True)
    account = create_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user, allow_live_trading=True)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, mode="live"),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "LIVE_DISABLED"
    assert body["risk_status"] == "REJECTED"
    assert body["events"][-1]["event_type"] == "LIVE_DISABLED"


def test_manual_live_order_requires_confirmation_text(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    user, token = create_authenticated_user(db_session, live_trading_enabled=True)
    account = create_live_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user, allow_live_trading=True)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, mode="live"),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "LIVE_DISABLED"
    assert "confirmation text is required" in body["events"][-1]["message"]


def test_strategy_live_order_remains_blocked(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    user, token = create_authenticated_user(db_session, live_trading_enabled=True, auto_trading_enabled=True)
    account = create_live_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user, allow_live_trading=True, allow_auto_trading=True)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(
            account,
            mode="live",
            source="strategy",
            confirmation_text="CONFIRM LIVE ORDER",
        ),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "LIVE_DISABLED"
    assert "Live auto trading is disabled by environment" in body["events"][-1]["message"]


def test_manual_live_market_order_remains_blocked(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    user, token = create_authenticated_user(db_session, live_trading_enabled=True)
    account = create_live_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user, allow_live_trading=True)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(
            account,
            mode="live",
            order_type="MARKET",
            price=None,
            confirmation_text="CONFIRM LIVE ORDER",
        ),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "RISK_REJECTED"
    assert "MARKET orders are not allowed" in body["events"][-1]["message"]


def test_manual_live_order_routes_to_broker_only_after_all_gates(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    LiveOrderHttpClient.post_calls = 0
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", LiveOrderHttpClient)
    user, token = create_authenticated_user(db_session, live_trading_enabled=True)
    account = create_live_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user, allow_live_trading=True)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(
            account,
            mode="live",
            correlation_id="manual_live_guarded_001",
            confirmation_text="CONFIRM LIVE ORDER",
        ),
    )

    assert response.status_code == 201
    body = response.json()["order"]
    assert body["status"] == "OPEN"
    assert body["risk_status"] == "APPROVED"
    assert body["broker_order_id"] == "zerodha_live_order_1"
    assert LiveOrderHttpClient.post_calls == 1

    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == account.id)).all()
    assert any(event.event_type == "broker.place_order.request" for event in audit_events)
    assert any(event.event_type == "broker.http.response" for event in audit_events)


def test_list_and_get_orders_return_user_orders(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)
    create_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, correlation_id="orders_list_001"),
    )
    order_id = create_response.json()["order"]["id"]

    list_response = client.get("/orders", headers={"Authorization": f"Bearer {token}"})
    get_response = client.get(f"/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})

    assert list_response.status_code == 200
    assert [order["id"] for order in list_response.json()] == [order_id]
    assert get_response.status_code == 200
    assert get_response.json()["correlation_id"] == "orders_list_001"


def test_cancel_order_updates_order_and_audit_log(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)
    create_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account),
    )
    order_id = create_response.json()["order"]["id"]

    response = client.post(f"/orders/{order_id}/cancel", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()["order"]
    assert body["status"] == "CANCELLED"
    assert body["events"][-1]["event_type"] == "CANCELLED"

    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == order_id)).all()
    assert any(event.event_type == "order.cancel_requested" for event in audit_events)
    assert any(event.event_type == "order.cancelled" for event in audit_events)


def test_modify_order_updates_order_and_event(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    account = create_broker_account(db_session, user)
    create_risk_profile(db_session, user)
    create_response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json=order_payload(account, price="2400"),
    )
    order_id = create_response.json()["order"]["id"]

    response = client.post(
        f"/orders/{order_id}/modify",
        headers={"Authorization": f"Bearer {token}"},
        json={"price": "2600"},
    )

    assert response.status_code == 200
    body = response.json()["order"]
    assert body["price"] == "2600.0000"
    assert body["events"][-1]["event_type"] == "MODIFIED"

    stored_order = db_session.get(Order, order_id)
    assert stored_order.price == Decimal("2600")
    assert db_session.scalar(select(OrderEvent).where(OrderEvent.order_id == order_id, OrderEvent.event_type == "MODIFIED")) is not None
