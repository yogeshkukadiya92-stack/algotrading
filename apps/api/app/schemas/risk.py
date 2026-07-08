from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.services.risk_engine import OrderSource, OrderType, RiskDecision, TradingMode


class EvaluateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    broker_account_id: str
    correlation_id: str
    symbol: str
    order_type: OrderType
    quantity: int
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    source: OrderSource
    mode: TradingMode
    lot_size: int = Field(default=1, gt=0)
    evaluation_time: datetime | None = None


class EvaluateOrderResponse(RiskDecision):
    pass
