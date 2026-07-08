from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.alerts import AlertResponse
from app.services.alerts import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    severity: str | None = None,
    alert_type: str | None = None,
    date_filter: date | None = Query(default=None, alias="date"),
) -> list[AlertResponse]:
    alerts = alert_service.list_alerts(
        db,
        current_user,
        severity=severity,
        alert_type=alert_type,
        created_on=date_filter,
    )
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.post("/{alert_id}/read", response_model=AlertResponse)
def mark_alert_read(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    return AlertResponse.model_validate(alert_service.mark_read(db, current_user, alert_id))


@router.post("/market-data-disconnected", response_model=AlertResponse)
def create_market_data_disconnected_alert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AlertResponse:
    alert = alert_service.create_alert(
        db,
        user_id=current_user.id,
        alert_type="market_data_disconnected",
        severity="WARN",
        title="Market data disconnected",
        message="Mock market data stream disconnected.",
        entity_type="market_data",
        entity_id=None,
    )
    db.commit()
    db.refresh(alert)
    return AlertResponse.model_validate(alert)
