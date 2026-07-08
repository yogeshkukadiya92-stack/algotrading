from pydantic import BaseModel, Field

from app.core.enums import Exchange, OrderType, TransactionSide


class StrategySignalCreate(BaseModel):
    correlation_id: str = Field(min_length=8, max_length=80)
    user_id: str = Field(min_length=1, max_length=80)
    strategy_id: str = Field(min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=80)
    exchange: Exchange = Exchange.NSE
    side: TransactionSide
    suggested_order_type: OrderType = OrderType.LIMIT
    quantity: int = Field(gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    reason: str = Field(min_length=1, max_length=500)


class StrategySignalResponse(BaseModel):
    accepted: bool
    message: str
    signal: StrategySignalCreate

