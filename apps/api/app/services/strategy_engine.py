from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditEvent, BrokerAccount, Order, Signal, Strategy, User
from app.schemas.orders import (
    Exchange,
    OrderCreateRequest,
    OrderSource,
    OrderType,
    ProductType,
    Segment,
    TradingMode,
    TransactionType,
)
from app.schemas.strategies import StrategyCreateRequest
from app.services.alerts import alert_service
from app.services.order_management import order_management_service
from app.services.system_controls import system_control_service


@dataclass(frozen=True)
class StrategyContext:
    strategy_id: str
    user_id: str
    config: dict[str, Any]


@dataclass(frozen=True)
class StrategySignal:
    symbol: str
    side: TransactionType
    quantity: int
    order_type: OrderType
    price: Decimal
    stop_loss: Decimal
    target: Decimal
    reason: str
    mode: TradingMode = TradingMode.PAPER


class StrategyInterface(ABC):
    name: str
    version: str

    @abstractmethod
    def on_start(self, context: StrategyContext) -> StrategySignal | None: ...

    @abstractmethod
    def on_tick(self, tick: dict, context: StrategyContext) -> StrategySignal | None: ...

    @abstractmethod
    def on_candle(self, candle: dict, context: StrategyContext) -> StrategySignal | None: ...

    @abstractmethod
    def on_order_update(self, order: Order, context: StrategyContext) -> StrategySignal | None: ...

    @abstractmethod
    def on_stop(self, context: StrategyContext) -> None: ...


class DemoStrategy(StrategyInterface):
    name = "DemoStrategy"
    version = "0.1.0"

    def on_start(self, context: StrategyContext) -> StrategySignal | None:
        if int(context.config.get("open_positions", 0)) >= 1:
            return None
        return StrategySignal(
            symbol=str(context.config.get("symbol", "NIFTY")),
            side=TransactionType.BUY,
            quantity=int(context.config.get("quantity", 1)),
            order_type=OrderType.LIMIT,
            price=Decimal(str(context.config.get("price", "24800"))),
            stop_loss=Decimal(str(context.config.get("stop_loss", "24750"))),
            target=Decimal(str(context.config.get("target", "24900"))),
            reason="DemoStrategy paper signal from mock start context",
        )

    def on_tick(self, tick: dict, context: StrategyContext) -> StrategySignal | None:
        return None

    def on_candle(self, candle: dict, context: StrategyContext) -> StrategySignal | None:
        return None

    def on_order_update(self, order: Order, context: StrategyContext) -> StrategySignal | None:
        return None

    def on_stop(self, context: StrategyContext) -> None:
        return None


class StrategyEngineService:
    def create_strategy(self, db: Session, user: User, payload: StrategyCreateRequest) -> Strategy:
        config = {
            "broker_account_id": payload.broker_account_id,
            "symbol": payload.symbol.upper(),
            "quantity": payload.quantity,
            "price": str(payload.price),
            "stop_loss": str(payload.stop_loss),
            "target": str(payload.target),
            "max_open_positions": 1,
            "open_positions": 0,
        }
        if payload.mode.value == "live":
            config.update(
                {
                    "max_daily_loss": str(payload.max_daily_loss),
                    "max_trades_per_day": payload.max_trades_per_day,
                    "max_open_positions": payload.max_open_positions,
                    "allowed_symbols": [symbol.upper() for symbol in (payload.allowed_symbols or [])],
                    "start_time": payload.start_time.isoformat() if payload.start_time else None,
                    "stop_time": payload.stop_time.isoformat() if payload.stop_time else None,
                    "live_auto_enabled_by_user": True,
                }
            )
        strategy = Strategy(
            user_id=user.id,
            name=payload.name,
            version=payload.version,
            status="CREATED",
            mode=payload.mode.value,
            config=config,
        )
        db.add(strategy)
        db.flush()
        db.add(
            AuditEvent(
                user_id=user.id,
                event_type="strategy.created",
                entity_type="strategy",
                entity_id=strategy.id,
                message=f"{payload.mode.value.upper()} strategy created",
                raw_payload={"name": payload.name, "mode": payload.mode.value},
            )
        )
        alert_service.create_alert(
            db,
            user_id=user.id,
            alert_type="strategy_started",
            severity="INFO",
            title="Strategy started",
            message=f"{strategy.name} created in {strategy.mode.upper()} mode.",
            entity_type="strategy",
            entity_id=strategy.id,
        )
        db.commit()
        db.refresh(strategy)
        return strategy

    def list_strategies(self, db: Session, user: User) -> list[Strategy]:
        return list(
            db.scalars(select(Strategy).where(Strategy.user_id == user.id).order_by(Strategy.created_at.desc())).all()
        )

    def get_strategy(self, db: Session, user: User, strategy_id: str) -> Strategy:
        strategy = db.scalar(select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id))
        if strategy is None:
            raise ValueError("Strategy not found")
        return strategy

    def start_strategy(self, db: Session, user: User, strategy_id: str) -> tuple[Strategy, Signal | None]:
        system_control_service.ensure_strategies_allowed(db, user)
        strategy = self.get_strategy(db, user, strategy_id)
        if strategy.status == "STOPPED":
            raise ValueError("Stopped strategy cannot be restarted in this phase")

        existing_signal = db.scalar(
            select(Signal)
            .where(Signal.strategy_id == strategy.id, Signal.user_id == user.id)
            .order_by(Signal.created_at.desc())
            .options(selectinload(Signal.order).selectinload(Order.events))
        )
        if existing_signal is not None:
            strategy.status = "RUNNING"
            db.add(
                AuditEvent(
                    user_id=user.id,
                    event_type="strategy.start_deduplicated",
                    entity_type="strategy",
                    entity_id=strategy.id,
                    message="Existing paper signal reused; no duplicate order created",
                    raw_payload={"signal_id": existing_signal.id, "order_id": existing_signal.order_id},
                )
            )
            db.commit()
            db.refresh(strategy)
            return strategy, existing_signal

        strategy.status = "RUNNING"
        context = StrategyContext(strategy_id=strategy.id, user_id=user.id, config=dict(strategy.config))
        emitted = DemoStrategy().on_start(context)
        signal = self._persist_and_route_signal(db, user, strategy, emitted) if emitted else None
        db.add(
            AuditEvent(
                user_id=user.id,
                event_type="strategy.started",
                entity_type="strategy",
                entity_id=strategy.id,
                message="Paper strategy started",
                raw_payload={"signal_id": signal.id if signal else None},
            )
        )
        alert_service.create_alert(
            db,
            user_id=user.id,
            alert_type="strategy_started",
            severity="INFO",
            title="Strategy started",
            message=f"{strategy.name} started in {strategy.mode.upper()} mode.",
            entity_type="strategy",
            entity_id=strategy.id,
        )
        db.commit()
        db.refresh(strategy)
        if signal:
            return strategy, self.get_signal(db, user, signal.id)
        return strategy, None

    def stop_strategy(self, db: Session, user: User, strategy_id: str) -> Strategy:
        strategy = self.get_strategy(db, user, strategy_id)
        strategy.status = "STOPPED"
        DemoStrategy().on_stop(StrategyContext(strategy_id=strategy.id, user_id=user.id, config=dict(strategy.config)))
        db.add(
            AuditEvent(
                user_id=user.id,
                event_type="strategy.stopped",
                entity_type="strategy",
                entity_id=strategy.id,
                message="Paper strategy stopped",
                raw_payload={},
            )
        )
        db.commit()
        db.refresh(strategy)
        return strategy

    def list_signals(self, db: Session, user: User, strategy_id: str) -> list[Signal]:
        self.get_strategy(db, user, strategy_id)
        return list(
            db.scalars(
                select(Signal)
                .where(Signal.strategy_id == strategy_id, Signal.user_id == user.id)
                .order_by(Signal.created_at.desc())
                .options(selectinload(Signal.order).selectinload(Order.events))
            ).all()
        )

    def get_signal(self, db: Session, user: User, signal_id: str) -> Signal:
        signal = db.scalar(
            select(Signal)
            .where(Signal.id == signal_id, Signal.user_id == user.id)
            .options(selectinload(Signal.order).selectinload(Order.events))
        )
        if signal is None:
            raise ValueError("Signal not found")
        return signal

    def _persist_and_route_signal(
        self,
        db: Session,
        user: User,
        strategy: Strategy,
        emitted: StrategySignal,
    ) -> Signal:
        signal_mode = TradingMode(strategy.mode)
        broker_account = self._resolve_strategy_broker_account(db, user, strategy)
        signal = Signal(
            strategy_id=strategy.id,
            user_id=user.id,
            symbol=emitted.symbol,
            side=emitted.side.value,
            quantity=emitted.quantity,
            order_type=emitted.order_type.value,
            price=emitted.price,
            stop_loss=emitted.stop_loss,
            target=emitted.target,
            reason=emitted.reason,
            mode=signal_mode.value,
            status="EMITTED",
        )
        db.add(signal)
        db.flush()
        order = order_management_service.create_order(
            db,
            user,
            OrderCreateRequest(
                broker_account_id=broker_account.id,
                correlation_id=f"strategy_{strategy.id}_{signal.id}_{uuid4().hex[:8]}",
                symbol=signal.symbol,
                exchange=Exchange.NSE,
                segment=Segment.EQ,
                transaction_type=TransactionType(signal.side),
                product_type=ProductType.MIS,
                order_type=OrderType(signal.order_type),
                quantity=signal.quantity,
                price=signal.price,
                source=OrderSource.STRATEGY,
                mode=signal_mode,
                strategy_id=strategy.id,
                strategy_version=strategy.version,
                algo_tag=f"{strategy.name}:{strategy.version}",
                lot_size=1,
            ),
        )
        signal.order_id = order.id
        signal.status = "ORDER_CREATED" if order.risk_status == "APPROVED" else "ORDER_REJECTED"
        db.flush()
        return signal

    def _resolve_strategy_broker_account(self, db: Session, user: User, strategy: Strategy) -> BrokerAccount:
        configured_id = strategy.config.get("broker_account_id")
        query = select(BrokerAccount).where(
            BrokerAccount.user_id == user.id,
            BrokerAccount.is_paper.is_(strategy.mode != "live"),
        )
        if configured_id:
            query = query.where(BrokerAccount.id == configured_id)
        account = db.scalar(query.order_by(BrokerAccount.created_at.desc()))
        if account is None:
            mode_label = "Live" if strategy.mode == "live" else "Paper"
            raise ValueError(f"{mode_label} broker account is required before starting a strategy")
        return account


strategy_engine_service = StrategyEngineService()
