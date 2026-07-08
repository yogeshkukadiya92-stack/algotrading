from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MarketDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TickDTO(MarketDataModel):
    symbol: str
    exchange: str
    segment: str
    ltp: Decimal
    bid: Decimal
    ask: Decimal
    volume: int
    oi: int
    timestamp: datetime


class CandleDTO(MarketDataModel):
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    start_time: datetime
