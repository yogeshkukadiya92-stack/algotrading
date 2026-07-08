from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode

from broker_core import (
    BrokerAdapter,
    BrokerName,
    BrokerNotImplementedError,
    BrokerSession,
    Exchange,
    Funds,
    NormalizedOrderStatus,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderResponseDTO,
    OrderStatusDTO,
    OrderSource,
    OrderType,
    PositionDTO,
    ProductType,
    Segment,
    TickDTO,
    BrokerProfile,
)


class BrokerHttpClient(Protocol):
    def get(self, path: str, headers: dict[str, str] | None = None) -> dict: ...

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict: ...


class ZerodhaReadOnlyAdapter(BrokerAdapter):
    """Read-only Zerodha adapter. Order-changing methods are intentionally disabled."""

    def __init__(
        self,
        *,
        api_key: str,
        access_token: str | None = None,
        redirect_uri: str | None = None,
        http_client: BrokerHttpClient,
    ) -> None:
        self.api_key = api_key
        self.access_token = access_token
        self.redirect_uri = redirect_uri
        self.http_client = http_client

    def login_url(self) -> str:
        query = {"api_key": self.api_key, "v": "3"}
        if self.redirect_uri:
            query["redirect_uri"] = self.redirect_uri
        return f"https://kite.zerodha.com/connect/login?{urlencode(query)}"

    def exchange_token(self, request_token: str) -> BrokerSession:
        return BrokerSession(
            broker_name=BrokerName.ZERODHA,
            access_token=f"session_placeholder_for_{request_token}",
            refresh_token=None,
            expires_at=None,
        )

    def get_profile(self) -> BrokerProfile:
        payload = self._get("/user/profile")
        data = payload.get("data", payload)
        return BrokerProfile(
            broker_name=BrokerName.ZERODHA,
            broker_user_id=str(data.get("user_id", "")),
            full_name=str(data.get("user_name") or data.get("full_name") or ""),
            email=data.get("email"),
        )

    def get_funds(self) -> Funds:
        payload = self._get("/user/margins")
        data = payload.get("data", payload)
        equity = data.get("equity", data)
        available = equity.get("available", {})
        utilised = equity.get("utilised", equity.get("utilized", {}))
        available_cash = self._decimal(available.get("cash", available.get("live_balance", "0")))
        collateral = self._decimal(available.get("collateral", "0"))
        utilized_margin = self._decimal(utilised.get("debits", utilised.get("margin", "0")))
        return Funds(
            broker_name=BrokerName.ZERODHA,
            available_cash=available_cash,
            collateral=collateral,
            utilized_margin=utilized_margin,
            net=self._decimal(equity.get("net", available_cash + collateral - utilized_margin)),
        )

    def get_positions(self) -> list[PositionDTO]:
        payload = self._get("/portfolio/positions")
        data = payload.get("data", payload)
        positions = data.get("net", data if isinstance(data, list) else [])
        return [self._position_from_raw(item) for item in positions]

    def get_orders(self) -> list[OrderStatusDTO]:
        payload = self._get("/orders")
        orders = payload.get("data", payload if isinstance(payload, list) else [])
        return [self._order_from_raw(item) for item in orders]

    def place_order(self, order: OrderRequestDTO) -> OrderResponseDTO:
        if order is None:
            raise BrokerNotImplementedError("Zerodha live place_order requires a valid order request")
        if order.mode.value != "live" or order.source not in {OrderSource.MANUAL, OrderSource.STRATEGY}:
            raise BrokerNotImplementedError("Zerodha live place_order only supports guarded manual or strategy live orders")
        if order.order_type not in {OrderType.LIMIT, OrderType.SL_LIMIT}:
            raise BrokerNotImplementedError("Zerodha live place_order only supports LIMIT and SL_LIMIT in this phase")

        payload = {
            "exchange": order.exchange.value,
            "tradingsymbol": order.symbol,
            "transaction_type": order.transaction_type.value,
            "quantity": order.quantity,
            "product": order.product_type.value,
            "order_type": order.order_type.value,
            "price": str(order.price) if order.price is not None else None,
            "trigger_price": str(order.trigger_price) if order.trigger_price is not None else None,
            "tag": order.tag or order.correlation_id,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        response = self.http_client.post("/orders/regular", data=payload, headers=self._headers())
        data = response.get("data", response)
        broker_order_id = str(data.get("order_id", ""))
        status = str(data.get("status", "OPEN"))
        return OrderResponseDTO(
            broker_order_id=broker_order_id or None,
            status=status,
            normalized_status=self._normalized_status(status),
            message=data.get("status_message"),
            correlation_id=order.correlation_id,
            raw_payload=response,
        )

    def modify_order(self, order_id: str, changes: OrderModifyRequestDTO) -> OrderResponseDTO:
        raise BrokerNotImplementedError("Zerodha live modify_order is disabled in this phase")

    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        raise BrokerNotImplementedError("Zerodha live cancel_order is disabled in this phase")

    def subscribe_market_data(self, instruments: list[str]) -> list[TickDTO]:
        raise BrokerNotImplementedError("Zerodha market data subscription is disabled in this phase")

    def _get(self, path: str) -> dict:
        return self.http_client.get(path, headers=self._headers())

    def _headers(self) -> dict[str, str]:
        headers = {"X-Kite-Version": "3"}
        if self.access_token:
            headers["Authorization"] = f"token {self.api_key}:{self.access_token}"
        return headers

    def _position_from_raw(self, item: dict) -> PositionDTO:
        return PositionDTO(
            broker_name=BrokerName.ZERODHA,
            exchange=self._exchange(item.get("exchange")),
            segment=self._segment(item.get("exchange")),
            symbol=str(item.get("tradingsymbol") or item.get("symbol") or ""),
            quantity=int(item.get("quantity", 0)),
            average_price=self._decimal(item.get("average_price", 0)),
            last_price=self._decimal(item.get("last_price", 0)),
            product_type=self._product_type(item.get("product")),
            realized_pnl=self._decimal(item.get("pnl", 0)),
            unrealized_pnl=self._decimal(item.get("m2m", item.get("unrealised", 0))),
        )

    def _order_from_raw(self, item: dict) -> OrderStatusDTO:
        return OrderStatusDTO(
            broker_order_id=str(item.get("order_id", "")),
            broker_status=str(item.get("status", "")),
            normalized_status=self._normalized_status(item.get("status")),
            filled_quantity=int(item.get("filled_quantity", 0)),
            pending_quantity=int(item.get("pending_quantity", 0)),
            average_price=self._optional_decimal(item.get("average_price")),
            message=item.get("status_message"),
            updated_at=self._optional_datetime(item.get("order_timestamp") or item.get("exchange_timestamp")),
        )

    def _normalized_status(self, status: object) -> NormalizedOrderStatus:
        value = str(status or "").upper()
        if value == "COMPLETE":
            return NormalizedOrderStatus.FILLED
        if value in {"OPEN", "TRIGGER PENDING"}:
            return NormalizedOrderStatus.OPEN if value == "OPEN" else NormalizedOrderStatus.TRIGGER_PENDING
        if value == "CANCELLED":
            return NormalizedOrderStatus.CANCELLED
        if value == "REJECTED":
            return NormalizedOrderStatus.REJECTED
        return NormalizedOrderStatus.RECEIVED

    def _exchange(self, value: object) -> Exchange:
        text = str(value or "NSE").upper()
        return Exchange.NFO if text == "NFO" else Exchange.BFO if text == "BFO" else Exchange.BSE if text == "BSE" else Exchange.NSE

    def _segment(self, exchange: object) -> Segment:
        return Segment.FNO if str(exchange or "").upper() in {"NFO", "BFO"} else Segment.EQ

    def _product_type(self, value: object) -> ProductType:
        text = str(value or "MIS").upper()
        if text == "CNC":
            return ProductType.CNC
        if text == "NRML":
            return ProductType.NRML
        return ProductType.MIS

    def _decimal(self, value: object) -> Decimal:
        return Decimal(str(value or "0"))

    def _optional_decimal(self, value: object) -> Decimal | None:
        return None if value is None else self._decimal(value)

    def _optional_datetime(self, value: object) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
