from decimal import Decimal

import pytest
from pydantic import ValidationError

from broker_core import (
    BrokerAdapter,
    BrokerName,
    Exchange,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderSource,
    OrderType,
    ProductType,
    Segment,
    TradingMode,
    TransactionType,
)


def build_order_request(**overrides) -> OrderRequestDTO:
    payload = {
        "broker_name": BrokerName.PAPER,
        "exchange": Exchange.NSE,
        "segment": Segment.EQ,
        "symbol": "RELIANCE",
        "transaction_type": TransactionType.BUY,
        "order_type": OrderType.LIMIT,
        "product_type": ProductType.MIS,
        "quantity": 10,
        "price": Decimal("2500"),
        "source": OrderSource.MANUAL,
        "mode": TradingMode.PAPER,
    }
    payload.update(overrides)
    return OrderRequestDTO(**payload)


def test_order_request_rejects_zero_quantity() -> None:
    with pytest.raises(ValidationError):
        build_order_request(quantity=0)


def test_order_request_rejects_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        build_order_request(quantity=-5)


def test_limit_order_requires_price() -> None:
    with pytest.raises(ValidationError, match="price is required for LIMIT order"):
        build_order_request(price=None, order_type=OrderType.LIMIT)


def test_sl_limit_order_requires_trigger_price() -> None:
    with pytest.raises(ValidationError, match="trigger_price is required for SL_LIMIT order"):
        build_order_request(order_type=OrderType.SL_LIMIT, trigger_price=None)


def test_market_order_is_rejected_when_source_is_strategy() -> None:
    with pytest.raises(ValidationError, match="MARKET orders are not allowed in strategy or algo mode"):
        build_order_request(order_type=OrderType.MARKET, price=None, source=OrderSource.STRATEGY)


def test_market_order_is_rejected_when_source_is_algo() -> None:
    with pytest.raises(ValidationError, match="MARKET orders are not allowed in strategy or algo mode"):
        build_order_request(order_type=OrderType.MARKET, price=None, source=OrderSource.ALGO)


def test_valid_limit_order_is_accepted() -> None:
    order = build_order_request()

    assert order.quantity == 10
    assert order.price == Decimal("2500")


def test_modify_request_quantity_must_be_positive_when_provided() -> None:
    with pytest.raises(ValidationError):
        OrderModifyRequestDTO(quantity=0)


def test_broker_adapter_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BrokerAdapter()
