from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BacktestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_name: str = "DemoStrategy"
    strategy_version: str = "0.1.0"
    symbol: str = "NIFTY"
    start_date: date = date(2026, 7, 1)
    end_date: date = date(2026, 7, 8)
    initial_capital: Decimal = Decimal("100000")
    quantity: int = Field(default=1, gt=0)
    stop_loss_points: Decimal = Decimal("40")
    target_points: Decimal = Decimal("80")

    @model_validator(mode="after")
    def validate_dates(self) -> BacktestCreateRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.strategy_name != "DemoStrategy":
            raise ValueError("Only DemoStrategy backtests are supported in this phase")
        return self


class BacktestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    strategy_name: str
    strategy_version: str
    symbol: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    net_pnl: Decimal
    max_drawdown: Decimal
    config: dict
    result: dict
    created_at: datetime
