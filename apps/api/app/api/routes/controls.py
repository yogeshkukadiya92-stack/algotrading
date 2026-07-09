from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import AuditEvent, Order, OrderEvent, User
from app.schemas.controls import (
    ControlStatusResponse,
    KillSwitchRequest,
    PaperSessionResetResponse,
    SystemControlResponse,
)
from app.services.system_controls import system_control_service

router = APIRouter(prefix="/controls", tags=["controls"])


@router.post("/kill-switch/enable", response_model=SystemControlResponse)
def enable_kill_switch(
    payload: KillSwitchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SystemControlResponse:
    control = system_control_service.enable_kill_switch(db, current_user, payload.reason)
    return SystemControlResponse.model_validate(control)


@router.post("/kill-switch/disable", response_model=SystemControlResponse)
def disable_kill_switch(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SystemControlResponse:
    control = system_control_service.disable_kill_switch(db, current_user)
    return SystemControlResponse.model_validate(control)


@router.get("/status", response_model=ControlStatusResponse)
def get_control_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ControlStatusResponse:
    control = system_control_service.get_status(db, current_user)
    return ControlStatusResponse(
        kill_switch_enabled=control.kill_switch_enabled,
        reason=control.reason,
        enabled_at=control.enabled_at,
        disabled_at=control.disabled_at,
    )


@router.post("/paper-session/reset", response_model=PaperSessionResetResponse)
def reset_paper_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperSessionResetResponse:
    now = datetime.now(UTC)
    open_statuses = {
        "CREATED",
        "RISK_APPROVED",
        "OPEN",
        "PENDING",
        "TRIGGER_PENDING",
        "PARTIALLY_FILLED",
    }
    orders = db.scalars(
        select(Order).where(
            Order.user_id == current_user.id,
            Order.mode == "paper",
            Order.status.in_(open_statuses),
        )
    ).all()

    for order in orders:
        previous_status = order.status
        order.status = "CANCELLED"
        db.add(
            OrderEvent(
                order_id=order.id,
                event_type="PAPER_SESSION_RESET",
                old_status=previous_status,
                new_status="CANCELLED",
                message="Paper session reset cancelled this open paper order.",
                raw_payload={"reset_at": now.isoformat()},
            )
        )

    db.add(
        AuditEvent(
            user_id=current_user.id,
            event_type="controls.paper_session_reset",
            entity_type="paper_session",
            entity_id=None,
            message="Paper session reset requested",
            raw_payload={"cancelled_orders": len(orders), "reset_at": now.isoformat()},
        )
    )
    db.commit()
    return PaperSessionResetResponse(
        reset_at=now,
        cancelled_orders=len(orders),
        message="Paper session reset complete. Historical orders and audit logs were kept.",
    )
