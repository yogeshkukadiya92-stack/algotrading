from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OrderSource(StrEnum):
    MANUAL = "manual"
    STRATEGY = "strategy"
    WEBHOOK = "webhook"


class TradingMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    BFO = "BFO"
    CDS = "CDS"
    MCX = "MCX"


class Segment(StrEnum):
    EQ = "EQ"
    FNO = "FNO"
    CURRENCY = "CURRENCY"
    COMMODITY = "COMMODITY"


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL_LIMIT = "SL_LIMIT"
    SL_MARKET = "SL_MARKET"


class ProductType(StrEnum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    broker_account_id: str
    correlation_id: str | None = None
    symbol: str
    exchange: Exchange = Exchange.NSE
    segment: Segment = Segment.EQ
    instrument_token: int | None = None
    transaction_type: TransactionType
    product_type: ProductType = ProductType.MIS
    order_type: OrderType
    quantity: int
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    source: OrderSource = OrderSource.MANUAL
    mode: TradingMode = TradingMode.PAPER
    strategy_id: str | None = None
    strategy_version: str | None = None
    algo_tag: str | None = None
    lot_size: int = Field(default=1, gt=0)
    confirmation_text: str | None = None
    confirmation_token: str | None = None


class OrderModifyRequest(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    price: Decimal | None = None
    trigger_price: Decimal | None = None


class OrderEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    old_status: str | None
    new_status: str | None
    message: str
    raw_payload: dict
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    correlation_id: str
    broker_account_id: str
    broker_name: str
    strategy_id: str | None = None
    strategy_version: str | None = None
    symbol: str
    exchange: str
    segment: str
    transaction_type: str
    product_type: str
    order_type: str
    quantity: int
    price: Decimal
    trigger_price: Decimal | None
    status: str
    broker_order_id: str | None
    risk_status: str
    algo_tag: str | None = None
    source: str
    mode: str
    created_at: datetime
    updated_at: datetime


class OrderDetailResponse(OrderResponse):
    events: list[OrderEventResponse] = []


class OrderActionResponse(BaseModel):
    order: OrderDetailResponse
    message: str


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    broker_account_id: str
    symbol: str
    quantity: int
    average_price: Decimal
    ltp: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    product_type: str
    updated_at: datetime
