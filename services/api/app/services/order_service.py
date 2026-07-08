from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import OrderStatus, ProductType, TradingMode
from app.models import Order, RiskProfile
from app.schemas.orders import OrderIntentCreate
from app.services.audit import AuditWriter
from app.services.brokers.base import BrokerAdapter
from app.services.brokers.live_disabled import LiveDisabledBrokerAdapter
from app.services.brokers.paper import PaperBrokerAdapter
from app.services.deduplication import DuplicateOrderGuard
from app.services.risk_engine import RiskEngine, RiskProfileSnapshot


class OrderPlacementService:
    def __init__(
        self,
        risk_engine: RiskEngine,
        paper_adapter: BrokerAdapter,
        live_adapter: BrokerAdapter,
    ) -> None:
        self.risk_engine = risk_engine
        self.paper_adapter = paper_adapter
        self.live_adapter = live_adapter

    @classmethod
    def from_settings(cls) -> "OrderPlacementService":
        settings = get_settings()
        return cls(
            risk_engine=RiskEngine(live_trading_enabled=settings.live_trading_enabled),
            paper_adapter=PaperBrokerAdapter(),
            live_adapter=LiveDisabledBrokerAdapter(),
        )

    def submit(self, db: Session, payload: OrderIntentCreate) -> Order:
        snapshot = payload.to_snapshot()
        audit = AuditWriter(db)
        idempotency_key = DuplicateOrderGuard.build_idempotency_key(snapshot)

        audit.record(
            "order.intent.received",
            snapshot.correlation_id,
            snapshot.user_id,
            snapshot.broker_account_id,
            payload=payload.model_dump(mode="json"),
        )

        profile = self._load_risk_profile(db, snapshot.user_id, snapshot.broker_account_id)
        day_notional = self._day_notional(db, snapshot.user_id, snapshot.broker_account_id)
        decision = self.risk_engine.evaluate(snapshot, profile, day_notional=day_notional)
        audit.record(
            "risk.decision",
            snapshot.correlation_id,
            snapshot.user_id,
            snapshot.broker_account_id,
            payload={
                "allowed": decision.allowed,
                "reasons": decision.reasons,
                "evaluated_rules": decision.evaluated_rules,
            },
            success=decision.allowed,
        )

        existing = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if existing is not None:
            audit.record(
                "order.duplicate_prevented",
                snapshot.correlation_id,
                snapshot.user_id,
                snapshot.broker_account_id,
                payload={"existing_order_id": existing.id, "idempotency_key": idempotency_key},
                success=True,
            )
            db.commit()
            db.refresh(existing)
            return existing

        order = self._build_order(payload, idempotency_key)
        db.add(order)

        if not decision.allowed:
            order.status = OrderStatus.REJECTED.value
            order.rejection_reason = "; ".join(decision.reasons)
            audit.record(
                "order.rejected",
                snapshot.correlation_id,
                snapshot.user_id,
                snapshot.broker_account_id,
                payload={"reasons": decision.reasons},
                success=False,
            )
            db.commit()
            db.refresh(order)
            return order

        adapter = self.paper_adapter if snapshot.mode == TradingMode.PAPER else self.live_adapter
        broker_request = {
            "adapter": adapter.name,
            "symbol": snapshot.symbol,
            "exchange": snapshot.exchange,
            "side": snapshot.side,
            "quantity": snapshot.quantity,
            "order_type": snapshot.order_type.value,
            "mode": snapshot.mode.value,
            "correlation_id": snapshot.correlation_id,
        }
        audit.record(
            "broker.place_order.request",
            snapshot.correlation_id,
            snapshot.user_id,
            snapshot.broker_account_id,
            request=broker_request,
        )

        try:
            broker_result = adapter.place_order(snapshot)
        except Exception as exc:
            order.status = OrderStatus.REJECTED.value
            order.rejection_reason = str(exc)
            audit.record(
                "broker.place_order.response",
                snapshot.correlation_id,
                snapshot.user_id,
                snapshot.broker_account_id,
                request=broker_request,
                response={"error": str(exc), "adapter": adapter.name},
                success=False,
            )
        else:
            order.status = broker_result.status.value
            order.broker_order_id = broker_result.broker_order_id
            audit.record(
                "broker.place_order.response",
                snapshot.correlation_id,
                snapshot.user_id,
                snapshot.broker_account_id,
                request=broker_request,
                response=broker_result.raw_response,
                success=True,
            )

        db.commit()
        db.refresh(order)
        return order

    def _build_order(self, payload: OrderIntentCreate, idempotency_key: str) -> Order:
        return Order(
            correlation_id=payload.correlation_id,
            user_id=payload.user_id,
            broker_account_id=payload.broker_account_id,
            client_order_key=payload.client_order_key,
            idempotency_key=idempotency_key,
            source=payload.source.value,
            mode=payload.mode.value,
            symbol=payload.symbol.upper(),
            exchange=payload.exchange.value,
            side=payload.side.value,
            order_type=payload.order_type.value,
            product=payload.product.value,
            quantity=payload.quantity,
            price=payload.price,
            estimated_price=payload.estimated_price,
            status=OrderStatus.RECEIVED.value,
            strategy_id=payload.strategy_id,
        )

    def _load_risk_profile(
        self, db: Session, user_id: str, broker_account_id: str
    ) -> RiskProfileSnapshot:
        row = db.scalar(
            select(RiskProfile).where(
                RiskProfile.user_id == user_id,
                RiskProfile.broker_account_id == broker_account_id,
            )
        )
        if row is None:
            return RiskProfileSnapshot()

        allowed_products = tuple(ProductType(item) for item in row.allowed_products)
        return RiskProfileSnapshot(
            is_configured=row.is_configured,
            allow_live_trading=row.allow_live_trading,
            max_order_quantity=row.max_order_quantity,
            max_order_value=row.max_order_value,
            max_day_notional=row.max_day_notional,
            allowed_products=allowed_products,
        )

    def _day_notional(self, db: Session, user_id: str, broker_account_id: str) -> Decimal:
        start = datetime.combine(datetime.now(UTC).date(), time.min, tzinfo=UTC)
        value = db.scalar(
            select(func.coalesce(func.sum(Order.quantity * Order.price), 0)).where(
                Order.user_id == user_id,
                Order.broker_account_id == broker_account_id,
                Order.created_at >= start,
                Order.status.in_([OrderStatus.ACCEPTED.value, OrderStatus.FILLED.value]),
            )
        )
        return Decimal(value or 0)

