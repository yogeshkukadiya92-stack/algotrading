from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from broker_core import (
    BrokerAuthError,
    BrokerError,
    BrokerName,
    BrokerNetworkError,
    BrokerNotImplementedError,
    BrokerRateLimitError,
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
from broker_upstox import UpstoxReadOnlyAdapter


class FakeHttpError(Exception):
    def __init__(self, message: str, *, status_code: int, code: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class FakeHttpClient:
    def __init__(self, responses: dict[str, dict] | None = None, error: Exception | None = None) -> None:
        self.responses = responses or {}
        self.error = error
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        self.calls.append((path, headers or {}))
        if self.error is not None:
            raise self.error
        return self.responses[path]

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        self.calls.append((path, headers or {}))
        if self.error is not None:
            raise self.error
        return self.responses[path]


def build_adapter(responses: dict[str, dict] | None = None, *, error: Exception | None = None) -> UpstoxReadOnlyAdapter:
    return UpstoxReadOnlyAdapter(
        api_key="upstox_test_key",
        access_token="upstox_test_token",
        redirect_uri="http://localhost:3000/brokers",
        http_client=FakeHttpClient(responses, error=error),
    )


def test_login_url_uses_client_id() -> None:
    adapter = build_adapter({})

    assert adapter.login_url().startswith("https://api.upstox.com/v2/login/authorization/dialog?")
    assert "client_id=upstox_test_key" in adapter.login_url()


def test_get_profile_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/v2/user/profile": {
                "status": "success",
                "data": {
                    "user_id": "U12345",
                    "first_name": "Read",
                    "last_name": "Only",
                    "email": "readonly@upstox.test",
                },
            }
        }
    )

    profile = adapter.get_profile()

    assert profile.broker_name == "upstox"
    assert profile.broker_user_id == "U12345"
    assert profile.full_name == "Read Only"
    assert profile.email == "readonly@upstox.test"


def test_get_funds_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/v2/user/get-funds-and-margin": {
                "status": "success",
                "data": {
                    "equity": {
                        "available_margin": 85000.25,
                        "collateral": 5000,
                        "used_margin": 2200.5,
                        "net": 87800.75,
                    }
                },
            }
        }
    )

    funds = adapter.get_funds()

    assert funds.broker_name == "upstox"
    assert funds.available_cash == Decimal("85000.25")
    assert funds.collateral == Decimal("5000")
    assert funds.utilized_margin == Decimal("2200.5")
    assert funds.net == Decimal("87800.75")


def test_get_positions_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/v2/portfolio/short-term-positions": {
                "status": "success",
                "data": [
                    {
                        "exchange": "NFO",
                        "trading_symbol": "NIFTY26JUL24800CE",
                        "quantity": 25,
                        "average_price": 104.5,
                        "last_price": 112.2,
                        "product_type": "NRML",
                        "realized_pnl": 110,
                        "unrealized_pnl": 192.5,
                    }
                ],
            }
        }
    )

    positions = adapter.get_positions()

    assert len(positions) == 1
    assert positions[0].symbol == "NIFTY26JUL24800CE"
    assert positions[0].exchange == "NFO"
    assert positions[0].segment == "FNO"
    assert positions[0].product_type == "NRML"


def test_get_orders_normalizes_response() -> None:
    adapter = build_adapter(
        {
            "/v2/order/retrieve-all": {
                "status": "success",
                "data": [
                    {
                        "order_id": "upx_order_1",
                        "status": "open",
                        "filled_quantity": 0,
                        "pending_quantity": 10,
                        "average_price": None,
                        "updated_at": "2026-07-08T11:20:00+00:00",
                    }
                ],
            }
        }
    )

    orders = adapter.get_orders()

    assert len(orders) == 1
    assert orders[0].broker_order_id == "upx_order_1"
    assert orders[0].normalized_status == NormalizedOrderStatus.OPEN
    assert orders[0].updated_at == datetime.fromisoformat("2026-07-08T11:20:00+00:00")


def test_subscribe_market_data_normalizes_quote_response() -> None:
    adapter = build_adapter(
        {
            "/v2/market-quote/quotes?symbol=NSE_EQ%7CRELIANCE%2CNSE_INDEX%7CNIFTY50": {
                "status": "success",
                "data": {
                    "NSE_EQ|RELIANCE": {
                        "exchange": "NSE",
                        "segment": "EQ",
                        "symbol": "NSE_EQ|RELIANCE",
                        "ltp": 2950.4,
                        "bid_price": 2950.1,
                        "ask_price": 2950.7,
                        "timestamp": "2026-07-08T11:21:00+00:00",
                        "volume": 1200,
                    }
                },
            }
        }
    )

    ticks = adapter.subscribe_market_data(["NSE_EQ|RELIANCE", "NSE_INDEX|NIFTY50"])

    assert len(ticks) == 1
    assert ticks[0].symbol == "NSE_EQ|RELIANCE"
    assert ticks[0].last_price == Decimal("2950.4")


def test_order_changing_methods_are_disabled() -> None:
    adapter = build_adapter({})

    with pytest.raises(BrokerNotImplementedError):
        adapter.place_order(
            OrderRequestDTO(
                correlation_id="corr_disabled",
                broker_name=BrokerName.UPSTOX,
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
    with pytest.raises(BrokerNotImplementedError):
        adapter.modify_order("order-1", None)  # type: ignore[arg-type]
    with pytest.raises(BrokerNotImplementedError):
        adapter.cancel_order("order-1")


def test_error_payload_maps_to_auth_error() -> None:
    adapter = build_adapter(
        {
            "/v2/user/profile": {
                "status": "error",
                "errors": [{"status_code": 401, "message": "Invalid token", "error_code": "UDAPI100050"}],
            }
        }
    )

    with pytest.raises(BrokerAuthError):
        adapter.get_profile()


def test_http_rate_limit_maps_to_broker_rate_limit_error() -> None:
    adapter = build_adapter(error=FakeHttpError("Too many requests", status_code=429))

    with pytest.raises(BrokerRateLimitError):
        adapter.get_orders()


def test_network_problem_maps_to_broker_network_error() -> None:
    adapter = build_adapter(error=RuntimeError("connection dropped"))

    with pytest.raises(BrokerNetworkError):
        adapter.get_funds()


def test_unknown_error_payload_maps_to_generic_broker_error() -> None:
    adapter = build_adapter(
        {
            "/v2/user/get-funds-and-margin": {
                "status": "error",
                "errors": [{"status_code": 500, "message": "Gateway issue", "error_code": "SERVER_ERROR"}],
            }
        }
    )

    with pytest.raises(BrokerError):
        adapter.get_funds()
