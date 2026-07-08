from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import BrokerAccount, Order, PnlSnapshot, Position, RiskProfile, User
from app.schemas.risk import EvaluateOrderRequest, EvaluateOrderResponse
from app.services.risk_engine import (
    PositionSnapshot,
    RecentOrderSnapshot,
    RiskEngine,
    RiskOrderRequest,
    RiskProfileSnapshot,
    RiskSeverity,
    RiskUser,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/evaluate-order", response_model=EvaluateOrderResponse)
def evaluate_order(
    payload: EvaluateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluateOrderResponse:
    broker_account = db.scalar(
        select(BrokerAccount).where(
            BrokerAccount.id == payload.broker_account_id,
            BrokerAccount.user_id == current_user.id,
        )
    )
    if broker_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker account not found")

    risk_profile = db.scalar(select(RiskProfile).where(RiskProfile.user_id == current_user.id))
    if risk_profile is None:
        return EvaluateOrderResponse(
            approved=False,
            rule="risk_profile_missing",
            reason="Risk profile is not configured for this user.",
            severity=RiskSeverity.BLOCK,
        )

    today = date.today()
    pnl_snapshot = db.scalar(
        select(PnlSnapshot).where(
            PnlSnapshot.user_id == current_user.id,
            PnlSnapshot.date == today,
        )
    )
    today_pnl = pnl_snapshot.total_pnl if pnl_snapshot is not None else Decimal("0")

    positions = db.scalars(
        select(Position).where(
            Position.user_id == current_user.id,
            Position.broker_account_id == broker_account.id,
        )
    ).all()

    recent_orders = db.scalars(
        select(Order).where(
            Order.user_id == current_user.id,
            func.date(Order.created_at) == today.isoformat(),
        )
    ).all()

    engine = RiskEngine()
    decision = engine.evaluate_order(
        RiskOrderRequest(
            broker_account_id=payload.broker_account_id,
            correlation_id=payload.correlation_id,
            symbol=payload.symbol,
            order_type=payload.order_type,
            quantity=payload.quantity,
            price=payload.price,
            trigger_price=payload.trigger_price,
            source=payload.source,
            mode=payload.mode,
            lot_size=payload.lot_size,
            broker_account_static_ip_verified=broker_account.static_ip_verified,
            evaluation_time=payload.evaluation_time,
        ),
        RiskUser(
            live_trading_enabled=current_user.live_trading_enabled,
            auto_trading_enabled=current_user.auto_trading_enabled,
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
        [RecentOrderSnapshot(correlation_id=order.correlation_id) for order in recent_orders],
    )

    return EvaluateOrderResponse(**decision.model_dump())
