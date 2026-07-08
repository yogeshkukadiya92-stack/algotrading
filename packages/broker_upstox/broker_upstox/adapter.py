from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode

from broker_core import (
    BrokerAdapter,
    BrokerAuthError,
    BrokerError,
    BrokerName,
    BrokerNetworkError,
    BrokerNotImplementedError,
    BrokerOrderRejectedError,
    BrokerProfile,
    BrokerRateLimitError,
    BrokerSession,
    Exchange,
    Funds,
    NormalizedOrderStatus,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderResponseDTO,
    OrderStatusDTO,
    PositionDTO,
    ProductType,
    Segment,
    TickDTO,
)


class BrokerHttpClient(Protocol):
    def get(self, path: str, headers: dict[str, str] | None = None) -> dict: ...

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict: ...


class UpstoxReadOnlyAdapter(BrokerAdapter):
    """Read-only Upstox adapter. Order-changing methods remain disabled in this phase."""

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
        query = {
            "client_id": self.api_key,
            "response_type": "code",
        }
        if self.redirect_uri:
            query["redirect_uri"] = self.redirect_uri
        return f"https://api.upstox.com/v2/login/authorization/dialog?{urlencode(query)}"

    def exchange_token(self, request_token: str) -> BrokerSession:
        return BrokerSession(
            broker_name=BrokerName.UPSTOX,
            access_token=f"session_placeholder_for_{request_token}",
            refresh_token=None,
            expires_at=None,
        )

    def get_profile(self) -> BrokerProfile:
        payload = self._get("/v2/user/profile")
        data = payload.get("data", payload)
        full_name = " ".join(part for part in [data.get("first_name"), data.get("last_name")] if part).strip()
        return BrokerProfile(
            broker_name=BrokerName.UPSTOX,
            broker_user_id=str(data.get("user_id") or data.get("client_id") or ""),
            full_name=full_name or str(data.get("user_name") or data.get("full_name") or ""),
            email=data.get("email"),
        )

    def get_funds(self) -> Funds:
        payload = self._get("/v2/user/get-funds-and-margin")
        data = payload.get("data", payload)
        equity = data.get("equity") or data
        available_cash = self._decimal(
            equity.get("available_margin")
            or equity.get("available_funds")
            or equity.get("available_cash")
            or 0
        )
        collateral = self._decimal(equity.get("collateral") or equity.get("used_collateral") or 0)
        utilized_margin = self._decimal(equity.get("used_margin") or equity.get("utilised_margin") or 0)
        return Funds(
            broker_name=BrokerName.UPSTOX,
            available_cash=available_cash,
            collateral=collateral,
            utilized_margin=utilized_margin,
            net=self._decimal(equity.get("net") or (available_cash + collateral - utilized_margin)),
        )

    def get_positions(self) -> list[PositionDTO]:
        payload = self._get("/v2/portfolio/short-term-positions")
        data = payload.get("data", payload)
        positions = data if isinstance(data, list) else data.get("positions", [])
        return [self._position_from_raw(item) for item in positions]

    def get_orders(self) -> list[OrderStatusDTO]:
        payload = self._get("/v2/order/retrieve-all")
        data = payload.get("data", payload)
        orders = data if isinstance(data, list) else data.get("orders", [])
        return [self._order_from_raw(item) for item in orders]

    def place_order(self, order: OrderRequestDTO) -> OrderResponseDTO:
        raise BrokerNotImplementedError("Upstox live place_order is disabled in this phase")

    def modify_order(self, order_id: str, changes: OrderModifyRequestDTO) -> OrderResponseDTO:
        raise BrokerNotImplementedError("Upstox live modify_order is disabled in this phase")

    def cancel_order(self, order_id: str) -> OrderResponseDTO:
        raise BrokerNotImplementedError("Upstox live cancel_order is disabled in this phase")

    def subscribe_market_data(self, instruments: list[str]) -> list[TickDTO]:
        query = urlencode({"symbol": ",".join(instruments)})
        payload = self._get(f"/v2/market-quote/quotes?{query}")
        data = payload.get("data", payload)
        quotes = data.values() if isinstance(data, dict) else data
        return [self._tick_from_raw(item) for item in quotes]

    def _get(self, path: str) -> dict:
        return self._request("get", path)

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        try:
            if method == "get":
                payload = self.http_client.get(path, headers=self._headers())
            else:
                payload = self.http_client.post(path, data=data, headers=self._headers())
        except Exception as exc:  # pragma: no cover - exercised through tests
            raise self._map_exception(exc) from exc
        self._raise_for_error_payload(payload)
        return payload

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if self.api_key:
            headers["Api-Version"] = "2.0"
        return headers

    def _raise_for_error_payload(self, payload: dict) -> None:
        status = str(payload.get("status", "")).lower()
        errors = payload.get("errors")
        if status != "error" and not errors:
            return

        error = (errors or [{}])[0]
        message = str(error.get("message") or payload.get("message") or "Broker request failed")
        code = str(error.get("error_code") or error.get("code") or "").lower()
        status_code = int(error.get("status_code") or payload.get("status_code") or 400)
        raise self._map_error(status_code=status_code, code=code, message=message)

    def _map_exception(self, exc: Exception) -> BrokerError:
        status_code = int(getattr(exc, "status_code", 0) or 0)
        message = str(exc)
        code = str(getattr(exc, "code", "") or "")
        if status_code:
            return self._map_error(status_code=status_code, code=code, message=message)
        return BrokerNetworkError(message or "Broker network request failed")

    def _map_error(self, *, status_code: int, code: str, message: str) -> BrokerError:
        lowered_code = code.lower()
        lowered_message = message.lower()
        if status_code in {401, 403} or "auth" in lowered_code or "token" in lowered_message:
            return BrokerAuthError(message)
        if status_code == 429 or "rate" in lowered_code:
            return BrokerRateLimitError(message)
        if status_code in {400, 409, 422} and ("order" in lowered_message or "reject" in lowered_message):
            return BrokerOrderRejectedError(message)
        return BrokerError(message)

    def _position_from_raw(self, item: dict) -> PositionDTO:
        segment = self._segment(item.get("segment") or item.get("instrument_type") or item.get("exchange"))
        return PositionDTO(
            broker_name=BrokerName.UPSTOX,
            exchange=self._exchange(item.get("exchange")),
            segment=segment,
            symbol=str(item.get("trading_symbol") or item.get("symbol") or item.get("instrument_key") or ""),
            quantity=int(item.get("quantity", 0)),
            average_price=self._decimal(item.get("average_price") or item.get("buy_price") or 0),
            last_price=self._decimal(item.get("last_price") or item.get("ltp") or 0),
            product_type=self._product_type(item.get("product") or item.get("product_type")),
            realized_pnl=self._decimal(item.get("realized_pnl") or item.get("pnl") or 0),
            unrealized_pnl=self._decimal(item.get("unrealized_pnl") or item.get("day_pnl") or 0),
        )

    def _order_from_raw(self, item: dict) -> OrderStatusDTO:
        status = str(item.get("status") or item.get("order_status") or "")
        return OrderStatusDTO(
            broker_order_id=str(item.get("order_id") or item.get("exchange_order_id") or ""),
            broker_status=status,
            normalized_status=self._normalized_status(status),
            filled_quantity=int(item.get("filled_quantity") or item.get("filled_qty") or 0),
            pending_quantity=int(item.get("pending_quantity") or item.get("pending_qty") or 0),
            average_price=self._optional_decimal(item.get("average_price")),
            message=item.get("status_message") or item.get("message"),
            updated_at=self._optional_datetime(item.get("order_timestamp") or item.get("updated_at")),
        )

    def _tick_from_raw(self, item: dict) -> TickDTO:
        instrument_key = str(item.get("symbol") or item.get("instrument_key") or "")
        return TickDTO(
            exchange=self._exchange(item.get("exchange")),
            segment=self._segment(item.get("segment") or item.get("exchange")),
            symbol=instrument_key,
            instrument_token=None,
            last_price=self._decimal(item.get("last_price") or item.get("ltp") or 0),
            bid_price=self._optional_decimal(item.get("bid_price") or item.get("bid")),
            ask_price=self._optional_decimal(item.get("ask_price") or item.get("ask")),
            last_trade_time=self._optional_datetime(item.get("last_trade_time") or item.get("timestamp")),
            volume=int(item.get("volume") or 0) if item.get("volume") is not None else None,
        )

    def _normalized_status(self, status: object) -> NormalizedOrderStatus:
        value = str(status or "").upper()
        if value in {"COMPLETE", "FILLED"}:
            return NormalizedOrderStatus.FILLED
        if value in {"OPEN", "ACTIVE"}:
            return NormalizedOrderStatus.OPEN
        if value in {"TRIGGER_PENDING", "TRIGGER PENDING"}:
            return NormalizedOrderStatus.TRIGGER_PENDING
        if value == "CANCELLED":
            return NormalizedOrderStatus.CANCELLED
        if value == "REJECTED":
            return NormalizedOrderStatus.REJECTED
        if value in {"PARTIALLY_FILLED", "PARTIALLY FILLED"}:
            return NormalizedOrderStatus.PARTIALLY_FILLED
        return NormalizedOrderStatus.RECEIVED

    def _exchange(self, value: object) -> Exchange:
        text = str(value or "NSE").upper()
        if text == "BSE":
            return Exchange.BSE
        if text == "NFO":
            return Exchange.NFO
        if text == "BFO":
            return Exchange.BFO
        if text == "CDS":
            return Exchange.CDS
        if text == "MCX":
            return Exchange.MCX
        return Exchange.NSE

    def _segment(self, value: object) -> Segment:
        text = str(value or "").upper()
        if any(marker in text for marker in {"NFO", "BFO", "FNO", "OPTION", "FUT"}):
            return Segment.FNO
        if any(marker in text for marker in {"CDS", "CURR"}):
            return Segment.CURRENCY
        if "MCX" in text:
            return Segment.COMMODITY
        return Segment.EQ

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
