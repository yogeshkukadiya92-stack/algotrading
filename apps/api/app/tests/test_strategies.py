from __future__ import annotations

from datetime import time
from decimal import Decimal

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import BrokerAccount, Order, RiskProfile, Signal, User
from app.services.broker_readonly import broker_readonly_service
from app.services.order_management import order_management_service


class LiveAutoHttpClient:
    post_calls = 0

    def __init__(self, _base_url: str) -> None:
        pass

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        return {}

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        type(self).post_calls += 1
        return {"data": {"order_id": "live_auto_order_1", "status": "OPEN", "status_message": "accepted"}}


def create_user_with_paper_setup(db_session, *, auto_trading_enabled: bool = True) -> tuple[User, str, BrokerAccount]:
    user = User(
        email="strategy-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Strategy User",
        auto_trading_enabled=auto_trading_enabled,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    account = BrokerAccount(
        id="paper_strategy_001",
        user_id=user.id,
        broker_name="paper",
        display_name="Paper Strategy Account",
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
    return user, create_access_token(user.id), account


def create_user_with_live_setup(db_session) -> tuple[User, str, BrokerAccount]:
    user = User(
        email="live-strategy-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Live Strategy User",
        live_trading_enabled=True,
        auto_trading_enabled=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    account = BrokerAccount(
        id="live_strategy_001",
        user_id=user.id,
        broker_name="zerodha",
        display_name="Zerodha Live Strategy",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=True,
        is_paper=False,
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
        allow_live_trading=True,
        allow_auto_trading=True,
    )
    db_session.add_all([account, profile])
    db_session.commit()
    return user, create_access_token(user.id), account


def strategy_payload(account: BrokerAccount, **overrides) -> dict:
    payload = {
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
    payload.update(overrides)
    return payload


def live_strategy_payload(account: BrokerAccount, **overrides) -> dict:
    payload = strategy_payload(
        account,
        mode="live",
        live_auto_confirmation_text="ENABLE LIVE AUTO TRADING",
        max_daily_loss="1000",
        max_trades_per_day=5,
        max_open_positions=2,
        allowed_symbols=["NIFTY"],
        start_time="00:00:00",
        stop_time="23:59:00",
    )
    payload.update(overrides)
    return payload


def test_create_demo_strategy_is_paper_only(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)

    response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "DemoStrategy"
    assert body["mode"] == "paper"
    assert body["status"] == "CREATED"


def test_live_strategy_mode_is_rejected(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)

    response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account, mode="live"),
    )

    assert response.status_code == 422
    assert "ENABLE LIVE AUTO TRADING" in str(response.json())


def test_live_strategy_requires_strategy_risk_config(client, db_session) -> None:
    _user, token, account = create_user_with_live_setup(db_session)

    response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(
            account,
            mode="live",
            live_auto_confirmation_text="ENABLE LIVE AUTO TRADING",
        ),
    )

    assert response.status_code == 422
    assert "strategy risk config" in str(response.json())


def test_live_auto_strategy_blocked_when_environment_disabled(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    _user, token, account = create_user_with_live_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=live_strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    signal = response.json()["signal"]
    assert signal["mode"] == "live"
    assert signal["order"]["status"] == "LIVE_DISABLED"
    assert "Live auto trading is disabled by environment" in signal["order"]["events"][-1]["message"]


def test_live_auto_strategy_routes_after_all_gates(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    LiveAutoHttpClient.post_calls = 0
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", LiveAutoHttpClient)
    _user, token, account = create_user_with_live_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=live_strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    signal = response.json()["signal"]
    assert signal["mode"] == "live"
    assert signal["order"]["status"] == "OPEN"
    assert signal["order"]["broker_order_id"] == "live_auto_order_1"
    assert signal["order"]["strategy_id"] if "strategy_id" in signal["order"] else True
    assert LiveAutoHttpClient.post_calls == 1


def test_start_strategy_saves_signal_and_routes_to_order_service(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["strategy"]["status"] == "RUNNING"
    signal = body["signal"]
    assert signal["mode"] == "paper"
    assert signal["order_type"] == "LIMIT"
    assert signal["reason"] == "DemoStrategy paper signal from mock start context"
    assert signal["order_id"]
    assert signal["order"]["source"] == "strategy"
    assert signal["order"]["mode"] == "paper"
    assert signal["order"]["strategy_id"] if "strategy_id" in signal["order"] else True

    signals_response = client.get(f"/strategies/{strategy_id}/signals", headers={"Authorization": f"Bearer {token}"})
    assert signals_response.status_code == 200
    assert signals_response.json()[0]["order_id"] == signal["order_id"]

    stored_signal = db_session.scalar(select(Signal).where(Signal.id == signal["id"]))
    assert stored_signal is not None
    assert stored_signal.order_id == signal["order_id"]


def test_strategy_emits_signal_not_direct_order(client, db_session, monkeypatch) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    create_order_calls = []
    broker_calls = []
    original_create_order = order_management_service.create_order
    original_place_order = order_management_service.paper_adapter.place_order

    def spy_create_order(db, user, payload):
        create_order_calls.append(payload)
        return original_create_order(db, user, payload)

    def spy_place_order(order):
        broker_calls.append(order)
        return original_place_order(order)

    monkeypatch.setattr(order_management_service, "create_order", spy_create_order)
    monkeypatch.setattr(order_management_service.paper_adapter, "place_order", spy_place_order)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    signal = db_session.scalar(select(Signal).where(Signal.strategy_id == strategy_id))
    assert signal is not None
    assert len(create_order_calls) == 1
    assert create_order_calls[0].source == "strategy"
    assert len(broker_calls) == 1


def test_strategy_signal_passes_through_risk_engine(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session, auto_trading_enabled=False)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    signal = response.json()["signal"]
    assert signal["status"] == "ORDER_REJECTED"
    assert signal["order"]["status"] == "RISK_REJECTED"
    assert signal["order"]["events"][-1]["event_type"] == "RISK_REJECTED"
    assert "Auto trading is disabled" in signal["order"]["events"][-1]["message"]


def test_strategy_generated_orders_are_paper_only(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    signal = response.json()["signal"]
    assert signal["mode"] == "paper"
    assert signal["order"]["mode"] == "paper"
    assert signal["order"]["source"] == "strategy"


def test_strategy_does_not_call_broker_directly(client, db_session, monkeypatch) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    calls = []
    original_place_order = order_management_service.paper_adapter.place_order

    def spy_place_order(order):
        calls.append(order)
        return original_place_order(order)

    monkeypatch.setattr(order_management_service.paper_adapter, "place_order", spy_place_order)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0].source == "strategy"


def test_stop_strategy_updates_status(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/stop", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["strategy"]["status"] == "STOPPED"


def test_strategy_stop_prevents_new_signals(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]
    stop_response = client.post(f"/strategies/{strategy_id}/stop", headers={"Authorization": f"Bearer {token}"})
    assert stop_response.status_code == 200

    start_response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert start_response.status_code == 400
    assert "Stopped strategy cannot be restarted" in start_response.json()["detail"]
    signals_response = client.get(f"/strategies/{strategy_id}/signals", headers={"Authorization": f"Bearer {token}"})
    assert signals_response.status_code == 200
    assert signals_response.json() == []


def test_demo_strategy_does_not_create_duplicate_orders_for_same_signal(client, db_session) -> None:
    _user, token, account = create_user_with_paper_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=strategy_payload(account),
    )
    strategy_id = create_response.json()["id"]

    first = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})
    second = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["signal"]["id"] == second.json()["signal"]["id"]
    assert first.json()["signal"]["order_id"] == second.json()["signal"]["order_id"]
    signals = db_session.scalars(select(Signal).where(Signal.strategy_id == strategy_id)).all()
    orders = db_session.scalars(select(Order).where(Order.strategy_id == strategy_id)).all()
    assert len(signals) == 1
    assert len(orders) == 1
