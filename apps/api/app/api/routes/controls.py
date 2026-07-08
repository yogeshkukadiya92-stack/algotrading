from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.controls import ControlStatusResponse, KillSwitchRequest, SystemControlResponse
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
