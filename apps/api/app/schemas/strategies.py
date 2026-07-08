from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.orders import OrderDetailResponse


class StrategyMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


LIVE_AUTO_CONFIRMATION_TEXT = "ENABLE LIVE AUTO TRADING"


class StrategyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = "DemoStrategy"
    version: str = "0.1.0"
    mode: StrategyMode = StrategyMode.PAPER
    broker_account_id: str | None = None
    symbol: str = "NIFTY"
    quantity: int = Field(default=1, gt=0)
    price: Decimal = Decimal("24800")
    stop_loss: Decimal = Decimal("24750")
    target: Decimal = Decimal("24900")
    max_daily_loss: Decimal | None = None
    max_trades_per_day: int | None = Field(default=None, gt=0)
    max_open_positions: int | None = Field(default=None, gt=0)
    allowed_symbols: list[str] | None = None
    start_time: time | None = None
    stop_time: time | None = None
    live_auto_confirmation_text: str | None = None

    @model_validator(mode="after")
    def validate_live_auto_gate(self) -> StrategyCreateRequest:
        if self.mode == StrategyMode.PAPER:
            return self

        if self.live_auto_confirmation_text != LIVE_AUTO_CONFIRMATION_TEXT:
            raise ValueError("LIVE strategy mode requires ENABLE LIVE AUTO TRADING confirmation")
        missing = [
            name
            for name, value in {
                "max_daily_loss": self.max_daily_loss,
                "max_trades_per_day": self.max_trades_per_day,
                "max_open_positions": self.max_open_positions,
                "allowed_symbols": self.allowed_symbols,
                "start_time": self.start_time,
                "stop_time": self.stop_time,
            }.items()
            if value in (None, [])
        ]
        if missing:
            raise ValueError(f"LIVE strategy mode requires strategy risk config: {', '.join(missing)}")
        return self


class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    version: str
    status: str
    mode: str
    config: dict
    created_at: datetime
    updated_at: datetime


class SignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    strategy_id: str
    order_id: str | None
    user_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Decimal
    stop_loss: Decimal | None
    target: Decimal | None
    reason: str
    mode: str
    status: str
    created_at: datetime
    order: OrderDetailResponse | None = None


class StrategyActionResponse(BaseModel):
    strategy: StrategyResponse
    signal: SignalResponse | None = None
    message: str
