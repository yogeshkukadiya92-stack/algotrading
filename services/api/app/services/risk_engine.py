from dataclasses import dataclass, field
from decimal import Decimal

from app.core.enums import OrderSource, OrderType, ProductType, TradingMode


@dataclass(frozen=True)
class OrderIntentSnapshot:
    correlation_id: str
    user_id: str
    broker_account_id: str
    source: OrderSource
    mode: TradingMode
    symbol: str
    exchange: str
    side: str
    quantity: int
    order_type: OrderType
    product: ProductType
    client_order_key: str
    price: Decimal | None = None
    estimated_price: Decimal | None = None
    strategy_id: str | None = None
    live_confirmation: bool = False


@dataclass(frozen=True)
class RiskProfileSnapshot:
    is_configured: bool = False
    allow_live_trading: bool = False
    max_order_quantity: int = 1000
    max_order_value: Decimal = Decimal("200000")
    max_day_notional: Decimal = Decimal("1000000")
    allowed_products: tuple[ProductType, ...] = (
        ProductType.CNC,
        ProductType.MIS,
        ProductType.NRML,
    )


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    evaluated_rules: list[str] = field(default_factory=list)


class RiskEngine:
    def __init__(self, live_trading_enabled: bool = False) -> None:
        self.live_trading_enabled = live_trading_enabled

    def evaluate(
        self,
        intent: OrderIntentSnapshot,
        profile: RiskProfileSnapshot,
        day_notional: Decimal = Decimal("0"),
    ) -> RiskDecision:
        reasons: list[str] = []
        rules = [
            "required_metadata",
            "algo_market_order_block",
            "live_trading_gates",
            "risk_profile_limits",
            "notional_limits",
        ]

        required_fields = {
            "correlation_id": intent.correlation_id,
            "user_id": intent.user_id,
            "broker_account_id": intent.broker_account_id,
            "source": intent.source,
            "mode": intent.mode,
            "client_order_key": intent.client_order_key,
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            reasons.append(f"Missing required order metadata: {', '.join(missing)}")

        if intent.quantity <= 0:
            reasons.append("Order quantity must be greater than zero")

        if intent.source == OrderSource.ALGO and intent.order_type == OrderType.MARKET:
            reasons.append("MARKET orders are not allowed in algo mode")

        if intent.order_type == OrderType.LIMIT and intent.price is None:
            reasons.append("LIMIT orders require a price")

        if intent.mode == TradingMode.LIVE:
            if not self.live_trading_enabled:
                reasons.append("Live trading is globally disabled")
            if not profile.is_configured:
                reasons.append("Live trading requires a configured risk profile")
            if not profile.allow_live_trading:
                reasons.append("Live trading is not enabled for this broker account")
            if not intent.live_confirmation:
                reasons.append("Live orders require explicit per-order confirmation")

        if intent.product not in profile.allowed_products:
            reasons.append(f"Product {intent.product} is not allowed by the risk profile")

        if intent.quantity > profile.max_order_quantity:
            reasons.append("Order quantity exceeds risk profile max_order_quantity")

        effective_price = intent.price or intent.estimated_price
        if effective_price is not None:
            if effective_price <= 0:
                reasons.append("Order price estimate must be greater than zero")
            else:
                order_value = effective_price * Decimal(intent.quantity)
                if order_value > profile.max_order_value:
                    reasons.append("Order value exceeds risk profile max_order_value")
                if day_notional + order_value > profile.max_day_notional:
                    reasons.append("Order would exceed risk profile max_day_notional")
        elif intent.mode == TradingMode.LIVE:
            reasons.append("Live orders require price or estimated_price for notional checks")

        return RiskDecision(allowed=not reasons, reasons=reasons, evaluated_rules=rules)

