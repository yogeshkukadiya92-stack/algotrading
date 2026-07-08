from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SupportedBroker(StrEnum):
    ZERODHA = "zerodha"
    UPSTOX = "upstox"


class BrokerConnectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    broker_name: SupportedBroker = SupportedBroker.ZERODHA
    display_name: str = "Zerodha Read Only"
    request_token: str | None = None


class BrokerAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    broker_name: str
    display_name: str
    is_active: bool
    is_paper: bool
    static_ip_verified: bool
    token_expires_at: datetime | None
    login_url: str | None = None
    status: str


class BrokerConnectResponse(BaseModel):
    account: BrokerAccountResponse
    login_url: str
    message: str


class BrokerProfileResponse(BaseModel):
    broker_name: str
    broker_user_id: str
    full_name: str
    email: str | None = None


class BrokerFundsResponse(BaseModel):
    broker_name: str
    available_cash: Decimal
    collateral: Decimal
    utilized_margin: Decimal
    net: Decimal


class BrokerPositionResponse(BaseModel):
    broker_name: str
    exchange: str
    segment: str
    symbol: str
    quantity: int
    average_price: Decimal
    last_price: Decimal
    product_type: str
    realized_pnl: Decimal
    unrealized_pnl: Decimal


class BrokerOrderStatusResponse(BaseModel):
    broker_order_id: str
    broker_status: str
    normalized_status: str
    filled_quantity: int
    pending_quantity: int
    average_price: Decimal | None
    message: str | None
    updated_at: datetime | None
