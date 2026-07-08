from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RiskSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    BLOCK = "BLOCK"


class TradingMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class OrderSource(StrEnum):
    MANUAL = "manual"
    API = "api"
    AUTO = "auto"
    ALGO = "algo"
    STRATEGY = "strategy"
    WEBHOOK = "webhook"
    SYSTEM = "system"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL_LIMIT = "SL_LIMIT"
    SL_MARKET = "SL_MARKET"


class RiskModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class RiskDecision(RiskModel):
    approved: bool
    rule: str
    reason: str
    severity: RiskSeverity


class RiskOrderRequest(RiskModel):
    correlation_id: str
    broker_account_id: str
    symbol: str
    order_type: OrderType
    quantity: int
    price: Decimal | None = None
    trigger_price: Decimal | None = None
    source: OrderSource
    mode: TradingMode
    lot_size: int = Field(default=1, gt=0)
    broker_account_static_ip_verified: bool = True
    evaluation_time: datetime | None = None


class RiskUser(RiskModel):
    live_trading_enabled: bool
    auto_trading_enabled: bool


class RiskProfile(RiskModel):
    max_daily_loss: Decimal
    max_order_value: Decimal
    max_lots_per_order: int
    max_trades_per_day: int
    max_open_positions: int
    allowed_start_time: time
    allowed_end_time: time
    allow_live_trading: bool
    allow_auto_trading: bool = False


class PositionSnapshot(RiskModel):
    symbol: str
    quantity: int


class RecentOrderSnapshot(RiskModel):
    correlation_id: str
