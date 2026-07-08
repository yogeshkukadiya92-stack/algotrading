from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Exchange, OrderSource, OrderStatus, OrderType, ProductType, TransactionSide, TradingMode
from app.services.risk_engine import OrderIntentSnapshot


class OrderIntentCreate(BaseModel):
    correlation_id: str = Field(min_length=8, max_length=80)
    user_id: str = Field(min_length=1, max_length=80)
    broker_account_id: str = Field(min_length=1, max_length=80)
    client_order_key: str = Field(min_length=8, max_length=128)
    source: OrderSource = OrderSource.MANUAL
    mode: TradingMode = TradingMode.PAPER
    symbol: str = Field(min_length=1, max_length=80)
    exchange: Exchange = Exchange.NSE
    side: TransactionSide
    order_type: OrderType
    product: ProductType = ProductType.MIS
    quantity: int = Field(gt=0)
    price: Decimal | None = Field(default=None, gt=0)
    estimated_price: Decimal | None = Field(default=None, gt=0)
    strategy_id: str | None = Field(default=None, max_length=80)
    live_confirmation: bool = False

    def to_snapshot(self) -> OrderIntentSnapshot:
        return OrderIntentSnapshot(
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            broker_account_id=self.broker_account_id,
            source=self.source,
            mode=self.mode,
            symbol=self.symbol.upper(),
            exchange=self.exchange.value,
            side=self.side.value,
            quantity=self.quantity,
            order_type=self.order_type,
            product=self.product,
            client_order_key=self.client_order_key,
            price=self.price,
            estimated_price=self.estimated_price,
            strategy_id=self.strategy_id,
            live_confirmation=self.live_confirmation,
        )


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    correlation_id: str
    user_id: str
    broker_account_id: str
    client_order_key: str
    source: str
    mode: str
    symbol: str
    exchange: str
    side: str
    order_type: str
    product: str
    quantity: int
    price: Decimal | None
    estimated_price: Decimal | None
    status: OrderStatus | str
    broker_order_id: str | None
    rejection_reason: str | None

