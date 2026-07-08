from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditEvent, BrokerAccount, Order, OrderEvent, PnlSnapshot, Position, RiskProfile, Signal, Strategy, User
from app.schemas.orders import OrderCreateRequest, OrderModifyRequest
from app.services.alerts import alert_service
from app.services.auto_trading_guard import auto_trading_guard
from app.services.broker_readonly import broker_readonly_service
from app.services.live_trading_guard import live_trading_guard
from app.services.risk_engine import (
    OrderSource as RiskOrderSource,
    OrderType as RiskOrderType,
    PositionSnapshot,
    RecentOrderSnapshot,
    RiskDecision,
    RiskEngine,
    RiskOrderRequest,
    RiskProfileSnapshot,
    RiskSeverity,
    RiskUser,
    TradingMode as RiskTradingMode,
)
from app.services.system_controls import KillSwitchActiveError, system_control_service

CURRENT_FILE = Path(__file__).resolve()
ROOT_CANDIDATES = [Path.cwd(), *CURRENT_FILE.parents, Path("/")]
for root_candidate in ROOT_CANDIDATES:
    for package_path in (
        root_candidate / "packages" / "broker_core",
        root_candidate / "services" / "paper_trading_service",
    ):
        if package_path.exists() and str(package_path) not in sys.path:
            sys.path.insert(0, str(package_path))

from broker_core import (  # noqa: E402
    BrokerName,
    BrokerOrderRejectedError,
    Exchange,
    OrderModifyRequestDTO,
    OrderRequestDTO,
    OrderSource,
    OrderType,
    ProductType,
    Segment,
    TradingMode,
    TransactionType,
)
from paper_trading_service import PaperTradingBrokerAdapter  # noqa: E402

from app.core.config import get_settings


CREATED = "CREATED"
RISK_APPROVED = "RISK_APPROVED"
RISK_REJECTED = "RISK_REJECTED"
LIVE_DISABLED = "LIVE_DISABLED"
CANCELLED = "CANCELLED"
MODIFIED = "MODIFIED"


class DuplicateCorrelationError(ValueError):
    pass


class IdempotencyConflictError(ValueError):
    pass


class DuplicateOrderRequestError(ValueError):
    pass


class OrderManagementService:
    def __init__(
        self,
        *,
        risk_engine: RiskEngine | None = None,
        paper_adapter: PaperTradingBrokerAdapter | None = None,
    ) -> None:
        self.risk_engine = risk_engine or RiskEngine()
        self.paper_adapter = paper_adapter or PaperTradingBrokerAdapter()

    def create_order(
        self,
        db: Session,
        user: User,
        payload: OrderCreateRequest,
        *,
        idempotency_key: str | None = None,
        request_id: str | None = None,
    ) -> Order:
        broker_account = self._get_broker_account(db, user, payload.broker_account_id)
        correlation_id = payload.correlation_id or f"corr_{uuid4().hex}"
        request_fingerprint = self._request_fingerprint(user, payload)

        if idempotency_key:
            existing_idempotent_order = db.scalar(
                select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key)
            )
            if existing_idempotent_order is not None:
                if existing_idempotent_order.request_fingerprint != request_fingerprint:
                    db.add(
                        AuditEvent(
                            user_id=user.id,
                            event_type="order.idempotency_conflict",
                            entity_type="order",
                            entity_id=existing_idempotent_order.id,
                            message="Idempotency key was reused with a different payload",
                            raw_payload={
                                "idempotency_key": idempotency_key,
                                "request_id": request_id,
                            },
                        )
                    )
                    db.commit()
                    raise IdempotencyConflictError("Idempotency key already used for a different order request")
                return self.get_order(db, user, existing_idempotent_order.id)

        existing_order = db.scalar(select(Order).where(Order.correlation_id == correlation_id))
        if existing_order is not None:
            db.add(
                AuditEvent(
                    user_id=user.id,
                    event_type="order.duplicate_rejected",
                    entity_type="order",
                    entity_id=existing_order.id,
                    message="Duplicate correlation_id rejected",
                    raw_payload={"correlation_id": correlation_id},
                )
            )
            db.commit()
            raise DuplicateCorrelationError("Duplicate correlation_id rejected")

        duplicate_order = self._find_recent_duplicate(
            db,
            user=user,
            broker_account=broker_account,
            request_fingerprint=request_fingerprint,
        )
        if duplicate_order is not None:
            db.add(
                AuditEvent(
                    user_id=user.id,
                    event_type="order.duplicate_rejected",
                    entity_type="order",
                    entity_id=duplicate_order.id,
                    message="Duplicate order request rejected",
                    raw_payload={
                        "request_fingerprint": request_fingerprint,
                        "idempotency_key": idempotency_key,
                        "request_id": request_id,
                    },
                )
            )
            db.commit()
            raise DuplicateOrderRequestError("Duplicate order request rejected")

        order = Order(
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            user_id=user.id,
            broker_account_id=broker_account.id,
            broker_name=broker_account.broker_name,
            strategy_id=payload.strategy_id,
            strategy_version=payload.strategy_version,
            symbol=payload.symbol,
            exchange=payload.exchange.value,
            segment=payload.segment.value,
            instrument_token=payload.instrument_token,
            transaction_type=payload.transaction_type.value,
            product_type=payload.product_type.value,
            order_type=payload.order_type.value,
            quantity=payload.quantity,
            price=payload.price or Decimal("0"),
            trigger_price=payload.trigger_price,
            status=CREATED,
            risk_status="PENDING",
            algo_tag=payload.algo_tag,
            source=payload.source.value,
            mode=payload.mode.value,
        )
        db.add(order)
        db.flush()
        self._add_order_event(db, order, "CREATED", None, CREATED, "Order request received")
        self._add_audit_event(
            db,
            user,
            "order.request_received",
            order,
            "Order request received by OMS",
            {
                "correlation_id": correlation_id,
                "idempotency_key": idempotency_key,
                "request_id": request_id,
                "source": order.source,
                "mode": order.mode,
            },
        )

        try:
            system_control_service.ensure_orders_allowed(db, user)
        except KillSwitchActiveError as exc:
            self._transition_order(
                db,
                user,
                order,
                RISK_REJECTED,
                "REJECTED",
                "KILL_SWITCH_REJECTED",
                str(exc),
                {"rule": "kill_switch", "reason": str(exc)},
            )
            db.commit()
            return self.get_order(db, user, order.id)

        risk_profile = db.scalar(select(RiskProfile).where(RiskProfile.user_id == user.id))
        decision = self._evaluate_risk(db, user, broker_account, order, payload, risk_profile)
        if not decision.approved:
            self._transition_order(
                db,
                user,
                order,
                RISK_REJECTED,
                "REJECTED",
                "RISK_REJECTED",
                decision.reason,
                decision.model_dump(),
            )
            db.commit()
            return self.get_order(db, user, order.id)

        self._transition_order(
            db,
            user,
            order,
            RISK_APPROVED,
            "APPROVED",
            "RISK_APPROVED",
            "Order approved by risk engine",
            decision.model_dump(),
        )

        if payload.mode.value == "live":
            return self._route_live_order(db, user, broker_account, order, payload, risk_profile)

        adapter_response = self.paper_adapter.place_order(self._to_broker_order_request(order))
        order.broker_order_id = adapter_response.broker_order_id
        self._transition_order(
            db,
            user,
            order,
            adapter_response.normalized_status.value,
            "APPROVED",
            "BROKER_RESPONSE",
            adapter_response.message or "Paper broker response stored",
            adapter_response.model_dump(),
        )
        db.commit()
        return self.get_order(db, user, order.id)

    def list_orders(self, db: Session, user: User) -> list[Order]:
        return list(
            db.scalars(
                select(Order)
                .where(Order.user_id == user.id)
                .order_by(Order.created_at.desc())
                .options(selectinload(Order.events))
            )
        )

    def get_order(self, db: Session, user: User, order_id: str) -> Order:
        order = db.scalar(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user.id)
            .options(selectinload(Order.events))
        )
        if order is None:
            raise ValueError("Order not found")
        return order

    def cancel_order(self, db: Session, user: User, order_id: str) -> Order:
        order = self.get_order(db, user, order_id)
        self._add_audit_event(db, user, "order.cancel_requested", order, "Order cancel requested", {})

        if order.status in {"FILLED", CANCELLED, RISK_REJECTED, LIVE_DISABLED}:
            self._add_audit_event(
                db,
                user,
                "order.cancel_rejected",
                order,
                "Order cannot be cancelled in its current state",
                {"status": order.status},
            )
            db.commit()
            return self.get_order(db, user, order.id)

        if order.mode == "paper" and order.broker_order_id:
            try:
                response = self.paper_adapter.cancel_order(order.broker_order_id)
                new_status = response.normalized_status.value
                raw_payload = response.model_dump()
            except BrokerOrderRejectedError as exc:
                self._add_audit_event(db, user, "order.cancel_rejected", order, str(exc), {})
                db.commit()
                return self.get_order(db, user, order.id)
        else:
            new_status = CANCELLED
            raw_payload = {}

        self._transition_order(db, user, order, new_status, order.risk_status, "CANCELLED", "Order cancelled", raw_payload)
        db.commit()
        return self.get_order(db, user, order.id)

    def modify_order(self, db: Session, user: User, order_id: str, payload: OrderModifyRequest) -> Order:
        order = self.get_order(db, user, order_id)
        self._add_audit_event(db, user, "order.modify_requested", order, "Order modify requested", payload.model_dump())

        if order.status == "FILLED":
            self._add_audit_event(db, user, "order.modify_rejected", order, "Filled order cannot be modified", {})
            db.commit()
            return self.get_order(db, user, order.id)

        if payload.quantity is not None:
            order.quantity = payload.quantity
        if payload.price is not None:
            order.price = payload.price
        if payload.trigger_price is not None:
            order.trigger_price = payload.trigger_price

        if order.mode == "paper" and order.broker_order_id:
            try:
                response = self.paper_adapter.modify_order(
                    order.broker_order_id,
                    OrderModifyRequestDTO(
                        quantity=payload.quantity,
                        price=payload.price,
                        trigger_price=payload.trigger_price,
                    ),
                )
                order.status = response.normalized_status.value
                raw_payload = response.model_dump()
            except BrokerOrderRejectedError as exc:
                self._add_audit_event(db, user, "order.modify_rejected", order, str(exc), {})
                db.commit()
                return self.get_order(db, user, order.id)
        else:
            order.status = MODIFIED
            raw_payload = payload.model_dump()

        self._add_order_event(db, order, "MODIFIED", None, order.status, "Order modified", raw_payload)
        self._add_audit_event(db, user, "order.modified", order, "Order modified", raw_payload)
        db.commit()
        return self.get_order(db, user, order.id)

    def _evaluate_risk(
        self,
        db: Session,
        user: User,
        broker_account: BrokerAccount,
        order: Order,
        payload: OrderCreateRequest,
        risk_profile: RiskProfile | None = None,
    ) -> RiskDecision:
        if risk_profile is None:
            return RiskDecision(
                approved=False,
                rule="risk_profile_missing",
                reason="Risk profile is not configured for this user.",
                severity=RiskSeverity.BLOCK,
            )

        today = date.today()
        pnl_snapshot = db.scalar(
            select(PnlSnapshot).where(PnlSnapshot.user_id == user.id, PnlSnapshot.date == today)
        )
        today_pnl = pnl_snapshot.total_pnl if pnl_snapshot is not None else Decimal("0")

        positions = db.scalars(
            select(Position).where(Position.user_id == user.id, Position.broker_account_id == broker_account.id)
        ).all()
        recent_orders = db.scalars(
            select(Order).where(
                Order.user_id == user.id,
                Order.id != order.id,
                func.date(Order.created_at) == today.isoformat(),
            )
        ).all()

        return self.risk_engine.evaluate_order(
            RiskOrderRequest(
                broker_account_id=broker_account.id,
                correlation_id=order.correlation_id,
                symbol=order.symbol,
                order_type=RiskOrderType(order.order_type),
                quantity=order.quantity,
                price=payload.price,
                trigger_price=payload.trigger_price,
                source=RiskOrderSource(order.source),
                mode=RiskTradingMode(order.mode),
                lot_size=payload.lot_size,
                broker_account_static_ip_verified=broker_account.static_ip_verified,
            ),
            RiskUser(
                live_trading_enabled=user.live_trading_enabled,
                auto_trading_enabled=user.auto_trading_enabled,
            ),
            RiskProfileSnapshot(
                max_daily_loss=risk_profile.max_daily_loss,
                max_order_value=risk_profile.max_order_value,
                max_lots_per_order=risk_profile.max_lots_per_order,
                max_trades_per_day=risk_profile.max_trades_per_day,
                max_open_positions=risk_profile.max_open_positions,
                allowed_start_time=risk_profile.allowed_start_time,
                allowed_end_time=risk_profile.allowed_end_time,
                allow_live_trading=risk_profile.allow_live_trading,
                allow_auto_trading=risk_profile.allow_auto_trading,
            ),
            [PositionSnapshot(symbol=position.symbol, quantity=position.quantity) for position in positions],
            today_pnl,
            [RecentOrderSnapshot(correlation_id=recent_order.correlation_id) for recent_order in recent_orders],
        )

    def _route_live_order(
        self,
        db: Session,
        user: User,
        broker_account: BrokerAccount,
        order: Order,
        payload: OrderCreateRequest,
        risk_profile: RiskProfile | None,
    ) -> Order:
        if order.source == "strategy":
            strategy = db.scalar(select(Strategy).where(Strategy.id == order.strategy_id, Strategy.user_id == user.id))
            recent_strategy_orders = db.scalars(
                select(Order).where(Order.user_id == user.id, Order.strategy_id == order.strategy_id, Order.id != order.id)
            ).all()
            recent_strategy_signals = db.scalars(
                select(Signal).where(Signal.user_id == user.id, Signal.strategy_id == order.strategy_id)
            ).all()
            guard_decision = auto_trading_guard.evaluate(
                db,
                user=user,
                broker_account=broker_account,
                risk_profile=risk_profile,
                strategy=strategy,
                payload=payload,
                recent_strategy_orders=list(recent_strategy_orders),
                recent_strategy_signals=list(recent_strategy_signals),
                strategy_open_positions=0,
                strategy_pnl=Decimal("0"),
                signal_uid=payload.correlation_id or order.correlation_id,
            )
        else:
            guard_decision = live_trading_guard.evaluate(
                db,
                user=user,
                broker_account=broker_account,
                risk_profile=risk_profile,
                payload=payload,
            )
        if not guard_decision.approved:
            return self._block_live_routing(db, user, order, guard_decision.rule, guard_decision.reason)

        try:
            adapter_response = broker_readonly_service.place_order(
                db,
                user,
                broker_account,
                self._to_broker_order_request(order),
            )
        except Exception as exc:
            return self._block_live_routing(db, user, order, "live_broker_order_failed", str(exc))

        order.broker_order_id = adapter_response.broker_order_id
        self._transition_order(
            db,
            user,
            order,
            adapter_response.normalized_status.value,
            "APPROVED",
            "BROKER_RESPONSE",
            adapter_response.message or "Live broker response stored",
            adapter_response.model_dump(),
        )
        db.commit()
        return self.get_order(db, user, order.id)

    def _block_live_routing(self, db: Session, user: User, order: Order, rule: str, reason: str) -> Order:
        self._transition_order(
            db,
            user,
            order,
            LIVE_DISABLED,
            "REJECTED",
            "LIVE_DISABLED",
            reason,
            {
                "rule": rule,
            },
        )
        db.commit()
        return self.get_order(db, user, order.id)

    def _transition_order(
        self,
        db: Session,
        user: User,
        order: Order,
        new_status: str,
        risk_status: str,
        event_type: str,
        message: str,
        raw_payload: dict,
    ) -> None:
        old_status = order.status
        order.status = new_status
        order.risk_status = risk_status
        self._add_order_event(db, order, event_type, old_status, new_status, message, raw_payload)
        self._add_audit_event(db, user, f"order.{event_type.lower()}", order, message, raw_payload)

    def _add_order_event(
        self,
        db: Session,
        order: Order,
        event_type: str,
        old_status: str | None,
        new_status: str | None,
        message: str,
        raw_payload: dict | None = None,
    ) -> None:
        db.add(
            OrderEvent(
                order_id=order.id,
                event_type=event_type,
                old_status=old_status,
                new_status=new_status,
                message=message,
                raw_payload=self._json_payload(raw_payload or {}),
            )
        )

    def _add_audit_event(
        self,
        db: Session,
        user: User,
        event_type: str,
        order: Order,
        message: str,
        raw_payload: dict,
    ) -> None:
        db.add(
            AuditEvent(
                user_id=user.id,
                event_type=event_type,
                entity_type="order",
                entity_id=order.id,
                message=message,
                raw_payload=self._json_payload(raw_payload),
            )
        )
        if event_type in {"order.risk_rejected", "order.kill_switch_rejected", "order.live_disabled"}:
            alert_service.create_alert(
                db,
                user_id=user.id,
                alert_type="risk_rejection" if event_type == "order.risk_rejected" else "order_rejected",
                severity="BLOCK",
                title="Order rejected",
                message=message,
                entity_type="order",
                entity_id=order.id,
            )
        elif event_type == "order.broker_response" and order.status == "FILLED":
            alert_service.create_alert(
                db,
                user_id=user.id,
                alert_type="order_filled",
                severity="INFO",
                title="Order filled",
                message=f"{order.transaction_type} {order.quantity} {order.symbol} filled in paper mode.",
                entity_type="order",
                entity_id=order.id,
            )

    def _get_broker_account(self, db: Session, user: User, broker_account_id: str) -> BrokerAccount:
        broker_account = db.scalar(
            select(BrokerAccount).where(BrokerAccount.id == broker_account_id, BrokerAccount.user_id == user.id)
        )
        if broker_account is None:
            raise ValueError("Broker account not found")
        return broker_account

    def _to_broker_order_request(self, order: Order) -> OrderRequestDTO:
        return OrderRequestDTO(
            correlation_id=order.correlation_id,
            broker_name=BrokerName(order.broker_name),
            exchange=Exchange(order.exchange),
            segment=Segment(order.segment),
            symbol=order.symbol,
            instrument_token=order.instrument_token,
            transaction_type=TransactionType(order.transaction_type),
            order_type=OrderType(order.order_type),
            product_type=ProductType(order.product_type),
            quantity=order.quantity,
            price=order.price if order.price != Decimal("0") else None,
            trigger_price=order.trigger_price,
            source=OrderSource(order.source),
            mode=TradingMode(order.mode),
            tag=order.algo_tag,
        )

    def _json_payload(self, payload: dict) -> dict:
        converted: dict = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                converted[key] = self._json_payload(value)
            elif isinstance(value, list):
                converted[key] = [self._json_payload(item) if isinstance(item, dict) else str(item) for item in value]
            elif isinstance(value, (str, int, float, bool)) or value is None:
                converted[key] = value
            else:
                converted[key] = str(value)
        return converted

    def _request_fingerprint(self, user: User, payload: OrderCreateRequest) -> str:
        normalized = self._json_payload(
            {
                "user_id": user.id,
                "broker_account_id": payload.broker_account_id,
                "symbol": payload.symbol.upper(),
                "exchange": payload.exchange.value,
                "segment": payload.segment.value,
                "instrument_token": payload.instrument_token,
                "transaction_type": payload.transaction_type.value,
                "product_type": payload.product_type.value,
                "order_type": payload.order_type.value,
                "quantity": payload.quantity,
                "price": payload.price,
                "trigger_price": payload.trigger_price,
                "source": payload.source.value,
                "mode": payload.mode.value,
                "strategy_id": payload.strategy_id,
                "strategy_version": payload.strategy_version,
                "algo_tag": payload.algo_tag,
            }
        )
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _find_recent_duplicate(
        self,
        db: Session,
        *,
        user: User,
        broker_account: BrokerAccount,
        request_fingerprint: str,
    ) -> Order | None:
        cutoff = datetime.now(UTC) - timedelta(seconds=get_settings().duplicate_order_window_seconds)
        return db.scalar(
            select(Order).where(
                Order.user_id == user.id,
                Order.broker_account_id == broker_account.id,
                Order.request_fingerprint == request_fingerprint,
                Order.created_at >= cutoff,
                Order.status.not_in({RISK_REJECTED, LIVE_DISABLED, CANCELLED}),
            )
        )


order_management_service = OrderManagementService()
