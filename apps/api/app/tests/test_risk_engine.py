from datetime import datetime, time
from decimal import Decimal

from app.services.risk_engine import (
    OrderSource,
    OrderType,
    PositionSnapshot,
    RecentOrderSnapshot,
    RiskEngine,
    RiskOrderRequest,
    RiskProfileSnapshot,
    RiskSeverity,
    RiskUser,
    TradingMode,
)


def build_order_request(**overrides) -> RiskOrderRequest:
    payload = {
        "correlation_id": "risk_corr_001",
        "broker_account_id": "broker_001",
        "symbol": "RELIANCE",
        "order_type": OrderType.LIMIT,
        "quantity": 10,
        "price": Decimal("2500"),
        "source": OrderSource.MANUAL,
        "mode": TradingMode.PAPER,
        "lot_size": 10,
        "broker_account_static_ip_verified": True,
        "evaluation_time": datetime(2026, 7, 8, 10, 0, 0),
    }
    payload.update(overrides)
    return RiskOrderRequest(**payload)


def build_user(**overrides) -> RiskUser:
    payload = {
        "live_trading_enabled": True,
        "auto_trading_enabled": True,
    }
    payload.update(overrides)
    return RiskUser(**payload)


def build_profile(**overrides) -> RiskProfileSnapshot:
    payload = {
        "max_daily_loss": Decimal("5000"),
        "max_order_value": Decimal("100000"),
        "max_lots_per_order": 5,
        "max_trades_per_day": 5,
        "max_open_positions": 3,
        "allowed_start_time": time(9, 15),
        "allowed_end_time": time(15, 20),
        "allow_live_trading": True,
        "allow_auto_trading": False,
    }
    payload.update(overrides)
    return RiskProfileSnapshot(**payload)


def test_blocks_live_order_when_user_live_trading_enabled_false() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(mode=TradingMode.LIVE),
        build_user(live_trading_enabled=False),
        build_profile(),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "user_live_trading_disabled"
    assert decision.reason == "Live trading is disabled for this user."
    assert decision.severity == RiskSeverity.BLOCK


def test_blocks_auto_order_when_user_auto_trading_enabled_false() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(source=OrderSource.STRATEGY),
        build_user(auto_trading_enabled=False),
        build_profile(),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "user_auto_trading_disabled"
    assert decision.reason == "Auto trading is disabled for this user."


def test_blocks_live_order_when_risk_profile_allow_live_trading_false() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(mode=TradingMode.LIVE),
        build_user(live_trading_enabled=True),
        build_profile(allow_live_trading=False),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "risk_profile_live_trading_disabled"


def test_blocks_market_order() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(order_type=OrderType.MARKET, price=None),
        build_user(),
        build_profile(),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "market_orders_not_allowed"


def test_blocks_zero_quantity() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(quantity=0),
        build_user(),
        build_profile(),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "quantity_must_be_positive"


def test_blocks_max_lots_exceeded() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(quantity=60),
        build_user(),
        build_profile(max_lots_per_order=5),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "max_lots_per_order_exceeded"


def test_blocks_max_order_value_exceeded() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(price=Decimal("15000")),
        build_user(),
        build_profile(max_order_value=Decimal("100000")),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "max_order_value_exceeded"


def test_blocks_max_daily_loss_reached() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(),
        build_user(),
        build_profile(max_daily_loss=Decimal("5000")),
        [],
        Decimal("-5000"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "max_daily_loss_reached"


def test_blocks_max_trades_per_day_reached() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(),
        build_user(),
        build_profile(max_trades_per_day=2),
        [],
        Decimal("0"),
        [
            RecentOrderSnapshot(correlation_id="recent_001"),
            RecentOrderSnapshot(correlation_id="recent_002"),
        ],
    )

    assert decision.approved is False
    assert decision.rule == "max_trades_per_day_reached"


def test_blocks_max_open_positions_reached() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(symbol="HDFCBANK"),
        build_user(),
        build_profile(max_open_positions=3),
        [
            PositionSnapshot(symbol="RELIANCE", quantity=10),
            PositionSnapshot(symbol="TCS", quantity=5),
            PositionSnapshot(symbol="INFY", quantity=3),
        ],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "max_open_positions_reached"


def test_blocks_duplicate_correlation_id() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(correlation_id="dup_001"),
        build_user(),
        build_profile(),
        [],
        Decimal("0"),
        [RecentOrderSnapshot(correlation_id="dup_001")],
    )

    assert decision.approved is False
    assert decision.rule == "duplicate_correlation_id"


def test_blocks_outside_trading_window() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(evaluation_time=datetime(2026, 7, 8, 8, 30, 0)),
        build_user(),
        build_profile(),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "outside_trading_window"


def test_blocks_live_order_when_static_ip_verified_false() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(mode=TradingMode.LIVE, broker_account_static_ip_verified=False),
        build_user(live_trading_enabled=True),
        build_profile(allow_live_trading=True),
        [],
        Decimal("0"),
        [],
    )

    assert decision.approved is False
    assert decision.rule == "static_ip_not_verified"


def test_approves_valid_paper_order() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(),
        build_user(),
        build_profile(),
        [PositionSnapshot(symbol="RELIANCE", quantity=10)],
        Decimal("1000"),
        [],
    )

    assert decision.approved is True
    assert decision.rule == "all_rules_passed"
    assert decision.reason == "Order approved by risk engine"
    assert decision.severity == RiskSeverity.INFO


def test_approves_valid_live_order_only_when_all_gates_enabled() -> None:
    decision = RiskEngine().evaluate_order(
        build_order_request(mode=TradingMode.LIVE),
        build_user(live_trading_enabled=True),
        build_profile(allow_live_trading=True),
        [PositionSnapshot(symbol="RELIANCE", quantity=10)],
        Decimal("0"),
        [],
    )

    assert decision.approved is True
    assert decision.rule == "all_rules_passed"
    assert decision.severity == RiskSeverity.INFO
