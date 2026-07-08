from __future__ import annotations

import pytest
from decimal import Decimal

from broker_core import (
    BrokerName,
    BrokerNotImplementedError,
    Exchange,
    NormalizedOrderStatus,
    OrderRequestDTO,
    OrderSource,
    OrderType,
    ProductType,
    Segment,
    TradingMode,
    TransactionType,
)
from broker_zerodha import ZerodhaReadOnlyAdapter


class FakeHttpClient:
    def __init__(self, responses: dict[str, dict]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        self.calls.append((path, headers or {}))
        return self.responses[path]

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        self.calls.append((path, headers or {}))
        return self.responses[path]


def build_adapter(responses: dict[str, dict]) -> ZerodhaReadOnlyAdapter:
    return ZerodhaReadOnlyAdapter(api_key="test_key", access_token="test_token", http_client=FakeHttpClient(responses))


def test_login_url_uses_api_key() -> None:
    adapter = build_adapter({})

    assert adapter.login_url().startswith("https://kite.zerodha.com/connect/login?")
    assert "api_key=test_key" in adapter.login_url()


def test_get_profile_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/user/profile": {
                "data": {
                    "user_id": "AB1234",
                    "user_name": "Readonly Trader",
                    "email": "readonly@example.test",
                }
            }
        }
    )

    profile = adapter.get_profile()

    assert profile.broker_name == "zerodha"
    assert profile.broker_user_id == "AB1234"
    assert profile.full_name == "Readonly Trader"
    assert profile.email == "readonly@example.test"


def test_get_funds_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/user/margins": {
                "data": {
                    "equity": {
                        "available": {"cash": 125000.5, "collateral": 10000},
                        "utilised": {"debits": 2500},
                        "net": 132500.5,
                    }
                }
            }
        }
    )

    funds = adapter.get_funds()

    assert str(funds.available_cash) == "125000.5"
    assert str(funds.collateral) == "10000"
    assert str(funds.utilized_margin) == "2500"
    assert str(funds.net) == "132500.5"


def test_get_positions_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/portfolio/positions": {
                "data": {
                    "net": [
                        {
                            "exchange": "NFO",
                            "tradingsymbol": "NIFTY26JUL3024800CE",
                            "quantity": 50,
                            "average_price": 101.5,
                            "last_price": 110,
                            "product": "NRML",
                            "pnl": 425,
                            "m2m": 425,
                        }
                    ]
                }
            }
        }
    )

    positions = adapter.get_positions()

    assert len(positions) == 1
    assert positions[0].symbol == "NIFTY26JUL3024800CE"
    assert positions[0].exchange == "NFO"
    assert positions[0].segment == "FNO"
    assert positions[0].product_type == "NRML"


def test_get_orders_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/orders": {
                "data": [
                    {
                        "order_id": "230101000001",
                        "status": "COMPLETE",
                        "filled_quantity": 10,
                        "pending_quantity": 0,
                        "average_price": 2500.25,
                    }
                ]
            }
        }
    )

    orders = adapter.get_orders()

    assert len(orders) == 1
    assert orders[0].broker_order_id == "230101000001"
    assert orders[0].normalized_status == NormalizedOrderStatus.FILLED


def test_order_changing_methods_are_disabled_even_when_live_flag_exists() -> None:
    adapter = build_adapter({})

    with pytest.raises(BrokerNotImplementedError):
        adapter.place_order(None)  # type: ignore[arg-type]
    with pytest.raises(BrokerNotImplementedError):
        adapter.modify_order("order-1", None)  # type: ignore[arg-type]
    with pytest.raises(BrokerNotImplementedError):
        adapter.cancel_order("order-1")


def test_manual_live_place_order_posts_normalized_payload() -> None:
    adapter = build_adapter({"/orders/regular": {"data": {"order_id": "live_1", "status": "OPEN"}}})

    response = adapter.place_order(
        OrderRequestDTO(
            correlation_id="corr_live_1",
            broker_name=BrokerName.ZERODHA,
            exchange=Exchange.NSE,
            segment=Segment.EQ,
            symbol="RELIANCE",
            transaction_type=TransactionType.BUY,
            order_type=OrderType.LIMIT,
            product_type=ProductType.MIS,
            quantity=1,
            price=Decimal("2500"),
            source=OrderSource.MANUAL,
            mode=TradingMode.LIVE,
        )
    )

    assert response.broker_order_id == "live_1"
    assert response.normalized_status == NormalizedOrderStatus.OPEN
    assert adapter.http_client.calls[-1][0] == "/orders/regular"
