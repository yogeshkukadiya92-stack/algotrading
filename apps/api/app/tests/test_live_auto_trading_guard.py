from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, BrokerAccount, RiskProfile, Strategy, SystemControl, User
from app.schemas.orders import OrderCreateRequest, OrderSource, OrderType, ProductType, TradingMode, TransactionType
from app.services.broker_readonly import broker_readonly_service
from app.services.auto_trading_guard import auto_trading_guard


class MockLiveAutoHttpClient:
    post_calls = 0

    def __init__(self, _base_url: str) -> None:
        pass

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        return {}

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        type(self).post_calls += 1
        return {"data": {"order_id": "live_auto_guarded_001", "status": "OPEN", "status_message": "accepted"}}


def create_live_auto_setup(
    db_session,
    *,
    user_live_enabled: bool = True,
    user_auto_enabled: bool = True,
    profile_live_enabled: bool = True,
    profile_auto_enabled: bool = True,
    strategy_mode: str = "live",
    strategy_status: str = "RUNNING",
    static_ip_verified: bool = True,
    allowed_symbols: list[str] | None = None,
    start_time_value: time = time(0, 0),
    stop_time_value: time = time(23, 59),
    max_daily_loss: str = "1000",
    max_trades_per_day: int = 5,
    max_open_positions: int = 2,
) -> tuple[User, str, BrokerAccount, RiskProfile, Strategy]:
    user = User(
        email=f"live-auto-{datetime.now().timestamp()}@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Live Auto User",
        live_trading_enabled=user_live_enabled,
        auto_trading_enabled=user_auto_enabled,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    account = BrokerAccount(
        id=f"live_auto_account_{user.id[:8]}",
        user_id=user.id,
        broker_name="zerodha",
        display_name="Zerodha Live Auto",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=static_ip_verified,
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
        allow_live_trading=profile_live_enabled,
        allow_auto_trading=profile_auto_enabled,
    )
    strategy = Strategy(
        user_id=user.id,
        name="DemoStrategy",
        version="0.1.0",
        status=strategy_status,
        mode=strategy_mode,
        config={
            "broker_account_id": account.id,
            "symbol": "NIFTY",
            "quantity": 1,
            "price": "24800",
            "stop_loss": "24750",
            "target": "24900",
            "max_daily_loss": max_daily_loss,
            "max_trades_per_day": max_trades_per_day,
            "max_open_positions": max_open_positions,
            "allowed_symbols": allowed_symbols or ["NIFTY"],
            "start_time": start_time_value.isoformat(),
            "stop_time": stop_time_value.isoformat(),
            "live_auto_enabled_by_user": True,
        },
    )
    db_session.add_all([account, profile, strategy])
    db_session.commit()
    db_session.refresh(account)
    db_session.refresh(profile)
    db_session.refresh(strategy)
    return user, create_access_token(user.id), account, profile, strategy


def build_live_auto_payload(
    account: BrokerAccount,
    strategy: Strategy | None,
    **overrides,
) -> OrderCreateRequest:
    payload = {
        "broker_account_id": account.id,
        "correlation_id": "live_auto_signal_001",
        "symbol": "NIFTY",
        "transaction_type": TransactionType.BUY,
        "product_type": ProductType.MIS,
        "order_type": OrderType.LIMIT,
        "quantity": 1,
        "price": Decimal("24800"),
        "source": OrderSource.STRATEGY,
        "mode": TradingMode.LIVE,
        "strategy_id": strategy.id if strategy else None,
        "strategy_version": strategy.version if strategy else None,
        "algo_tag": "DemoStrategy:0.1.0",
        "lot_size": 1,
    }
    payload.update(overrides)
    return OrderCreateRequest(**payload)


def evaluate_live_auto(db_session, monkeypatch, *, payload_overrides: dict | None = None, setup_overrides: dict | None = None, strategy=None):
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    user, _token, account, profile, persisted_strategy = create_live_auto_setup(db_session, **(setup_overrides or {}))
    active_strategy = strategy if strategy is not None else persisted_strategy
    payload = build_live_auto_payload(account, active_strategy, **(payload_overrides or {}))
    decision = auto_trading_guard.evaluate(
        db_session,
        user=user,
        broker_account=account,
        risk_profile=profile,
        strategy=active_strategy,
        payload=payload,
        recent_strategy_orders=[],
        recent_strategy_signals=[],
        strategy_open_positions=0,
        strategy_pnl=Decimal("0"),
        signal_uid=payload.correlation_id or "live_auto_signal_001",
    )
    return decision, user, account, profile, active_strategy, payload


def future_exclusion_window() -> tuple[time, time]:
    now = datetime.now()
    if now.hour < 21:
        start = (now + timedelta(hours=1)).time().replace(microsecond=0)
        stop = (now + timedelta(hours=2)).time().replace(microsecond=0)
    else:
        start = (now - timedelta(hours=2)).time().replace(microsecond=0)
        stop = (now - timedelta(hours=1)).time().replace(microsecond=0)
    return start, stop


def live_strategy_create_payload(account: BrokerAccount, **overrides) -> dict:
    payload = {
        "name": "DemoStrategy",
        "version": "0.1.0",
        "mode": "live",
        "broker_account_id": account.id,
        "symbol": "NIFTY",
        "quantity": 1,
        "price": "24800",
        "stop_loss": "24750",
        "target": "24900",
        "live_auto_confirmation_text": "ENABLE LIVE AUTO TRADING",
        "max_daily_loss": "1000",
        "max_trades_per_day": 5,
        "max_open_positions": 2,
        "allowed_symbols": ["NIFTY"],
        "start_time": "00:00:00",
        "stop_time": "23:59:00",
    }
    payload.update(overrides)
    return payload


def test_auto_live_blocked_when_enable_auto_trading_false(db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.delenv("ENABLE_AUTO_TRADING", raising=False)
    user, _token, account, profile, strategy = create_live_auto_setup(db_session)
    payload = build_live_auto_payload(account, strategy)

    decision = auto_trading_guard.evaluate(
        db_session,
        user=user,
        broker_account=account,
        risk_profile=profile,
        strategy=strategy,
        payload=payload,
        recent_strategy_orders=[],
        recent_strategy_signals=[],
        strategy_open_positions=0,
        strategy_pnl=Decimal("0"),
        signal_uid=payload.correlation_id or "live_auto_signal_001",
    )

    assert decision.approved is False
    assert decision.rule == "auto_trading_env_disabled"


def test_auto_live_blocked_when_user_auto_trading_disabled(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        setup_overrides={"user_auto_enabled": False},
    )

    assert decision.approved is False
    assert decision.rule == "user_auto_trading_disabled"


def test_auto_live_blocked_when_risk_profile_allow_auto_trading_false(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        setup_overrides={"profile_auto_enabled": False},
    )

    assert decision.approved is False
    assert decision.rule == "risk_profile_auto_disabled"


def test_auto_live_blocked_when_strategy_mode_is_paper(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        setup_overrides={"strategy_mode": "paper"},
    )

    assert decision.approved is False
    assert decision.rule == "strategy_not_live"


def test_auto_live_blocked_when_strategy_is_stopped(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        setup_overrides={"strategy_status": "STOPPED"},
    )

    assert decision.approved is False
    assert decision.rule == "strategy_not_running"


def test_auto_live_blocked_without_strategy_id(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        payload_overrides={"strategy_id": None},
    )

    assert decision.approved is False
    assert decision.rule == "strategy_id_required"


def test_auto_live_blocked_without_strategy_version(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        payload_overrides={"strategy_version": None},
    )

    assert decision.approved is False
    assert decision.rule == "strategy_version_required"


def test_auto_live_blocked_without_algo_tag(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        payload_overrides={"algo_tag": None},
    )

    assert decision.approved is False
    assert decision.rule == "algo_tag_required"


def test_auto_live_blocked_for_market_order(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        payload_overrides={"order_type": OrderType.MARKET, "price": None},
    )

    assert decision.approved is False
    assert decision.rule == "auto_order_type_not_allowed"


def test_auto_live_blocked_when_strategy_max_loss_reached(db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    user, _token, account, profile, strategy = create_live_auto_setup(db_session, max_daily_loss="1000")
    payload = build_live_auto_payload(account, strategy)

    decision = auto_trading_guard.evaluate(
        db_session,
        user=user,
        broker_account=account,
        risk_profile=profile,
        strategy=strategy,
        payload=payload,
        recent_strategy_orders=[],
        recent_strategy_signals=[],
        strategy_open_positions=0,
        strategy_pnl=Decimal("-1000"),
        signal_uid=payload.correlation_id or "live_auto_signal_001",
    )

    assert decision.approved is False
    assert decision.rule == "strategy_max_loss_reached"


def test_auto_live_blocked_when_strategy_max_trades_reached(db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    user, _token, account, profile, strategy = create_live_auto_setup(db_session, max_trades_per_day=2)
    payload = build_live_auto_payload(account, strategy)
    recent_orders = [SimpleNamespace(correlation_id="a"), SimpleNamespace(correlation_id="b")]

    decision = auto_trading_guard.evaluate(
        db_session,
        user=user,
        broker_account=account,
        risk_profile=profile,
        strategy=strategy,
        payload=payload,
        recent_strategy_orders=recent_orders,
        recent_strategy_signals=[],
        strategy_open_positions=0,
        strategy_pnl=Decimal("0"),
        signal_uid=payload.correlation_id or "live_auto_signal_001",
    )

    assert decision.approved is False
    assert decision.rule == "strategy_max_trades_reached"


def test_auto_live_blocked_for_disallowed_symbol(db_session, monkeypatch) -> None:
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        setup_overrides={"allowed_symbols": ["BANKNIFTY"]},
    )

    assert decision.approved is False
    assert decision.rule == "symbol_not_allowed"


def test_auto_live_blocked_outside_strategy_time_window(db_session, monkeypatch) -> None:
    start, stop = future_exclusion_window()
    decision, *_ = evaluate_live_auto(
        db_session,
        monkeypatch,
        setup_overrides={"start_time_value": start, "stop_time_value": stop},
    )

    assert decision.approved is False
    assert decision.rule == "outside_strategy_window"


def test_auto_live_blocked_when_kill_switch_enabled(db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    user, _token, account, profile, strategy = create_live_auto_setup(db_session)
    control = SystemControl(user_id=user.id, kill_switch_enabled=True, reason="Emergency stop")
    db_session.add(control)
    db_session.commit()
    payload = build_live_auto_payload(account, strategy)

    decision = auto_trading_guard.evaluate(
        db_session,
        user=user,
        broker_account=account,
        risk_profile=profile,
        strategy=strategy,
        payload=payload,
        recent_strategy_orders=[],
        recent_strategy_signals=[],
        strategy_open_positions=0,
        strategy_pnl=Decimal("0"),
        signal_uid=payload.correlation_id or "live_auto_signal_001",
    )

    assert decision.approved is False
    assert decision.rule == "kill_switch_enabled"


def test_valid_live_auto_limit_signal_passes_all_gates_using_mocked_broker_adapter(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    MockLiveAutoHttpClient.post_calls = 0
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", MockLiveAutoHttpClient)

    _user, token, account, _profile, _strategy = create_live_auto_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=live_strategy_create_payload(account),
    )
    strategy_id = create_response.json()["id"]

    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    signal = response.json()["signal"]
    order = signal["order"]
    assert signal["mode"] == "live"
    assert signal["order_type"] == "LIMIT"
    assert order["status"] == "OPEN"
    assert order["mode"] == "live"
    assert order["source"] == "strategy"
    assert order["strategy_id"] == strategy_id
    assert order["strategy_version"] == "0.1.0"
    assert order["algo_tag"] == "DemoStrategy:0.1.0"
    assert order["broker_order_id"] == "live_auto_guarded_001"
    assert MockLiveAutoHttpClient.post_calls == 1


def test_duplicate_signal_id_is_rejected(db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    user, _token, account, profile, strategy = create_live_auto_setup(db_session)
    payload = build_live_auto_payload(account, strategy, correlation_id="duplicate_signal_001")
    recent_orders = [SimpleNamespace(correlation_id="duplicate_signal_001")]

    decision = auto_trading_guard.evaluate(
        db_session,
        user=user,
        broker_account=account,
        risk_profile=profile,
        strategy=strategy,
        payload=payload,
        recent_strategy_orders=recent_orders,
        recent_strategy_signals=[],
        strategy_open_positions=0,
        strategy_pnl=Decimal("0"),
        signal_uid="duplicate_signal_001",
    )

    assert decision.approved is False
    assert decision.rule == "duplicate_signal_id"


def test_every_live_auto_order_creates_audit_event(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_LIVE_BROKER_ORDERS", "true")
    monkeypatch.setenv("ENABLE_AUTO_TRADING", "true")
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    MockLiveAutoHttpClient.post_calls = 0
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", MockLiveAutoHttpClient)

    _user, token, account, _profile, _strategy = create_live_auto_setup(db_session)
    create_response = client.post(
        "/strategies",
        headers={"Authorization": f"Bearer {token}"},
        json=live_strategy_create_payload(account),
    )
    strategy_id = create_response.json()["id"]
    response = client.post(f"/strategies/{strategy_id}/start", headers={"Authorization": f"Bearer {token}"})
    order_id = response.json()["signal"]["order"]["id"]

    audit_events = db_session.scalars(
        select(AuditEvent).where(AuditEvent.entity_type == "order", AuditEvent.entity_id == order_id)
    ).all()

    assert {event.event_type for event in audit_events} >= {
        "order.request_received",
        "order.risk_approved",
        "order.broker_response",
    }
