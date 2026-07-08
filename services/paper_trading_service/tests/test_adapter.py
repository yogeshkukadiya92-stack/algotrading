from decimal import Decimal

import pytest

from broker_core import (
    BrokerName,
    BrokerOrderRejectedError,
    Exchange,
    NormalizedOrderStatus,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderSource,
    OrderType,
    ProductType,
    Segment,
    TradingMode,
    TransactionType,
)
from paper_trading_service import PaperTradingBrokerAdapter


def build_order(**overrides) -> OrderRequestDTO:
    payload = {
        "correlation_id": "paper_corr_001",
        "broker_name": BrokerName.PAPER,
        "exchange": Exchange.NSE,
        "segment": Segment.EQ,
        "symbol": "RELIANCE",
        "transaction_type": TransactionType.BUY,
        "order_type": OrderType.LIMIT,
        "product_type": ProductType.MIS,
        "quantity": 10,
        "price": Decimal("100"),
        "source": OrderSource.MANUAL,
        "mode": TradingMode.PAPER,
    }
    payload.update(overrides)
    return OrderRequestDTO(**payload)


def test_limit_buy_fills_when_ask_is_less_than_or_equal_to_limit_price() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("99"), ask_price=Decimal("100"))

    response = adapter.place_order(build_order(price=Decimal("100")))

    assert response.normalized_status == NormalizedOrderStatus.FILLED
    status = adapter.get_orders()[0]
    assert status.filled_quantity == 10
    assert status.average_price == Decimal("100")


def test_limit_buy_does_not_fill_when_ask_is_greater_than_limit_price() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("101"), bid_price=Decimal("100"), ask_price=Decimal("101"))

    response = adapter.place_order(build_order(price=Decimal("100")))

    assert response.normalized_status == NormalizedOrderStatus.OPEN
    status = adapter.get_orders()[0]
    assert status.filled_quantity == 0
    assert status.pending_quantity == 10


def test_limit_sell_fills_when_bid_is_greater_than_or_equal_to_limit_price() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("100"), ask_price=Decimal("101"))

    response = adapter.place_order(
        build_order(
            transaction_type=TransactionType.SELL,
            price=Decimal("100"),
        )
    )

    assert response.normalized_status == NormalizedOrderStatus.FILLED
    status = adapter.get_orders()[0]
    assert status.filled_quantity == 10
    assert status.average_price == Decimal("100")


def test_limit_sell_does_not_fill_when_bid_is_less_than_limit_price() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("99"), bid_price=Decimal("99"), ask_price=Decimal("100"))

    response = adapter.place_order(
        build_order(
            transaction_type=TransactionType.SELL,
            price=Decimal("100"),
        )
    )

    assert response.normalized_status == NormalizedOrderStatus.OPEN
    status = adapter.get_orders()[0]
    assert status.filled_quantity == 0
    assert status.pending_quantity == 10


def test_cancel_order_works_before_fill() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("101"), bid_price=Decimal("100"), ask_price=Decimal("101"))
    response = adapter.place_order(build_order(price=Decimal("100")))

    cancel_response = adapter.cancel_order(response.broker_order_id)
    adapter.update_market_data("RELIANCE", ltp=Decimal("99"), bid_price=Decimal("98"), ask_price=Decimal("99"))

    assert cancel_response.normalized_status == NormalizedOrderStatus.CANCELLED
    status = adapter.get_orders()[0]
    assert status.normalized_status == NormalizedOrderStatus.CANCELLED
    assert status.filled_quantity == 0
    assert [event.new_status for event in adapter.get_order_events(response.broker_order_id)] == [
        NormalizedOrderStatus.OPEN,
        NormalizedOrderStatus.CANCELLED,
    ]


def test_filled_order_cannot_be_cancelled() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("99"), ask_price=Decimal("100"))
    response = adapter.place_order(build_order(price=Decimal("100")))

    with pytest.raises(BrokerOrderRejectedError, match="Filled paper order cannot be cancelled"):
        adapter.cancel_order(response.broker_order_id)


def test_filled_order_cannot_be_modified() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("99"), ask_price=Decimal("100"))
    response = adapter.place_order(build_order(price=Decimal("100")))

    with pytest.raises(BrokerOrderRejectedError, match="Filled paper order cannot be modified"):
        adapter.modify_order(response.broker_order_id, OrderModifyRequestDTO(price=Decimal("101")))


def test_sl_limit_triggers_correctly() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("100"), ask_price=Decimal("101"))

    response = adapter.place_order(
        build_order(
            transaction_type=TransactionType.SELL,
            order_type=OrderType.SL_LIMIT,
            price=Decimal("94"),
            trigger_price=Decimal("95"),
        )
    )
    assert response.normalized_status == NormalizedOrderStatus.TRIGGER_PENDING

    adapter.update_market_data("RELIANCE", ltp=Decimal("95"), bid_price=Decimal("95"), ask_price=Decimal("96"))

    status = adapter.get_orders()[0]
    assert status.normalized_status == NormalizedOrderStatus.FILLED
    assert status.average_price == Decimal("95")
    assert [event.new_status for event in adapter.get_order_events(response.broker_order_id)] == [
        NormalizedOrderStatus.TRIGGER_PENDING,
        NormalizedOrderStatus.OPEN,
        NormalizedOrderStatus.FILLED,
    ]


def test_position_average_price_updates_correctly() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("99"), ask_price=Decimal("100"))
    adapter.place_order(build_order(quantity=10, price=Decimal("100")))

    adapter.update_market_data("RELIANCE", ltp=Decimal("120"), bid_price=Decimal("119"), ask_price=Decimal("120"))
    adapter.place_order(
        build_order(
            correlation_id="paper_corr_002",
            quantity=10,
            price=Decimal("120"),
        )
    )

    position = adapter.get_positions()[0]
    assert position.quantity == 20
    assert position.average_price == Decimal("110")


def test_pnl_calculation_works_for_simple_buy_sell() -> None:
    adapter = PaperTradingBrokerAdapter()
    adapter.update_market_data("RELIANCE", ltp=Decimal("100"), bid_price=Decimal("99"), ask_price=Decimal("100"))
    adapter.place_order(build_order(quantity=10, price=Decimal("100")))

    adapter.update_market_data("RELIANCE", ltp=Decimal("110"), bid_price=Decimal("110"), ask_price=Decimal("111"))
    adapter.place_order(
        build_order(
            correlation_id="paper_corr_sell_001",
            transaction_type=TransactionType.SELL,
            quantity=5,
            price=Decimal("110"),
        )
    )

    position = adapter.get_positions()[0]
    assert position.quantity == 5
    assert position.average_price == Decimal("100")
    assert position.realized_pnl == Decimal("50")
    assert position.unrealized_pnl == Decimal("50")
