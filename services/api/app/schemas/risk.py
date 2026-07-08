from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ProductType


class RiskProfileUpsert(BaseModel):
    user_id: str = Field(min_length=1, max_length=80)
    broker_account_id: str = Field(min_length=1, max_length=80)
    is_configured: bool = True
    allow_live_trading: bool = False
    max_order_quantity: int = Field(gt=0, default=1000)
    max_order_value: Decimal = Field(gt=0, default=Decimal("200000"))
    max_day_notional: Decimal = Field(gt=0, default=Decimal("1000000"))
    allowed_products: list[ProductType] = Field(
        default_factory=lambda: [ProductType.CNC, ProductType.MIS, ProductType.NRML]
    )


class RiskProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    broker_account_id: str
    is_configured: bool
    allow_live_trading: bool
    max_order_quantity: int
    max_order_value: Decimal
    max_day_notional: Decimal
    allowed_products: list[str]

