from decimal import Decimal

from app.core.enums import OrderSource, OrderType, ProductType, TradingMode
from app.services.risk_engine import OrderIntentSnapshot, RiskEngine, RiskProfileSnapshot


def make_intent(**overrides) -> OrderIntentSnapshot:
    values = {
        "correlation_id": "corr_test_001",
        "user_id": "user_1",
        "broker_account_id": "zerodha_main",
        "source": OrderSource.MANUAL,
        "mode": TradingMode.PAPER,
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "side": "buy",
        "quantity": 10,
        "order_type": OrderType.LIMIT,
        "product": ProductType.MIS,
        "client_order_key": "client_order_001",
        "price": Decimal("3000"),
        "estimated_price": Decimal("3000"),
        "strategy_id": None,
        "live_confirmation": False,
    }
    values.update(overrides)
    return OrderIntentSnapshot(**values)


def test_paper_limit_order_allowed_with_default_profile() -> None:
    decision = RiskEngine().evaluate(make_intent(), RiskProfileSnapshot())

    assert decision.allowed is True
    assert decision.reasons == []


def test_algo_market_orders_are_blocked() -> None:
    intent = make_intent(source=OrderSource.ALGO, order_type=OrderType.MARKET, price=None)

    decision = RiskEngine().evaluate(intent, RiskProfileSnapshot())

    assert decision.allowed is False
    assert "MARKET orders are not allowed in algo mode" in decision.reasons


def test_live_trading_is_disabled_by_default() -> None:
    intent = make_intent(mode=TradingMode.LIVE, live_confirmation=True)
    profile = RiskProfileSnapshot(is_configured=True, allow_live_trading=True)

    decision = RiskEngine(live_trading_enabled=False).evaluate(intent, profile)

    assert decision.allowed is False
    assert "Live trading is globally disabled" in decision.reasons


def test_live_order_requires_profile_enablement_and_confirmation() -> None:
    intent = make_intent(mode=TradingMode.LIVE, live_confirmation=False)
    profile = RiskProfileSnapshot(is_configured=False, allow_live_trading=False)

    decision = RiskEngine(live_trading_enabled=True).evaluate(intent, profile)

    assert decision.allowed is False
    assert "Live trading requires a configured risk profile" in decision.reasons
    assert "Live trading is not enabled for this broker account" in decision.reasons
    assert "Live orders require explicit per-order confirmation" in decision.reasons


def test_live_order_can_pass_only_when_all_gates_are_open() -> None:
    intent = make_intent(mode=TradingMode.LIVE, live_confirmation=True)
    profile = RiskProfileSnapshot(is_configured=True, allow_live_trading=True)

    decision = RiskEngine(live_trading_enabled=True).evaluate(intent, profile)

    assert decision.allowed is True


def test_limit_order_requires_price() -> None:
    decision = RiskEngine().evaluate(make_intent(price=None), RiskProfileSnapshot())

    assert decision.allowed is False
    assert "LIMIT orders require a price" in decision.reasons


def test_order_value_limit_is_enforced() -> None:
    profile = RiskProfileSnapshot(max_order_value=Decimal("10000"))

    decision = RiskEngine().evaluate(make_intent(quantity=10, price=Decimal("3000")), profile)

    assert decision.allowed is False
    assert "Order value exceeds risk profile max_order_value" in decision.reasons

