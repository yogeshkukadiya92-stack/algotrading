from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from broker_core.enums import (
    BrokerName,
    Exchange,
    NormalizedOrderStatus,
    OrderSource,
    OrderType,
    ProductType,
    Segment,
    TradingMode,
    TransactionType,
)


class BrokerModel(BaseModel):
    model_config = ConfigDict(use_enum_values=False, extra="forbid")


class BrokerProfile(BrokerModel):
    broker_name: BrokerName
    broker_user_id: str
    full_name: str
    email: str | None = None


class BrokerSession(BrokerModel):
    broker_name: BrokerName
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None


class Funds(BrokerModel):
    broker_name: BrokerName
    available_cash: Decimal
    collateral: Decimal = Decimal("0")
    utilized_margin: Decimal = Decimal("0")
    net: Decimal


class PositionDTO(BrokerModel):
    broker_name: BrokerName
    exchange: Exchange
    segment: Segment
    symbol: str
    quantity: int
    average_price: Decimal
    last_price: Decimal
    product_type: ProductType
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")


class OrderRequestDTO(BrokerModel):
    correlation_id: str | None = None
    broker_name: BrokerName
    exchange: Exchange
    segment: Segment
    symbol: str
    instrument_token: int | None = None
    transaction_type: TransactionType
    order_type: OrderType
    product_type: ProductType
    quantity: int = Field(gt=0)
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    source: OrderSource
    mode: TradingMode
    tag: str | None = None

    @model_validator(mode="after")
    def validate_order_constraints(self) -> OrderRequestDTO:
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for LIMIT order")

        if self.order_type == OrderType.SL_LIMIT and self.trigger_price is None:
            raise ValueError("trigger_price is required for SL_LIMIT order")

        if self.order_type == OrderType.MARKET and self.source in {OrderSource.ALGO, OrderSource.STRATEGY}:
            raise ValueError("MARKET orders are not allowed in strategy or algo mode")

        return self


class OrderModifyRequestDTO(BrokerModel):
    quantity: int | None = Field(default=None, gt=0)
    price: Decimal | None = None
    trigger_price: Decimal | None = None


class OrderResponseDTO(BrokerModel):
    broker_order_id: str | None = None
    status: str
    normalized_status: NormalizedOrderStatus
    message: str | None = None
    correlation_id: str | None = None
    raw_payload: dict = Field(default_factory=dict)


class OrderStatusDTO(BrokerModel):
    broker_order_id: str
    broker_status: str
    normalized_status: NormalizedOrderStatus
    filled_quantity: int = 0
    pending_quantity: int = 0
    average_price: Decimal | None = None
    message: str | None = None
    updated_at: datetime | None = None


class TickDTO(BrokerModel):
    exchange: Exchange
    segment: Segment
    symbol: str
    instrument_token: int | None = None
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    last_trade_time: datetime | None = None
    volume: int | None = None


class CandleDTO(BrokerModel):
    exchange: Exchange
    segment: Segment
    symbol: str
    interval: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
