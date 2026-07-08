from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import BrokerAccount, User
from app.schemas.brokers import (
    BrokerAccountResponse,
    BrokerConnectRequest,
    BrokerConnectResponse,
    BrokerFundsResponse,
    BrokerOrderStatusResponse,
    BrokerPositionResponse,
    BrokerProfileResponse,
)
from app.services.broker_readonly import broker_readonly_service
from app.services.alerts import alert_service
from broker_core import BrokerNotImplementedError

router = APIRouter(prefix="/brokers", tags=["brokers"])


@router.get("", response_model=list[BrokerAccountResponse])
def list_brokers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BrokerAccountResponse]:
    accounts = broker_readonly_service.list_accounts(db, current_user)
    return [broker_account_response(account) for account in accounts]


@router.post("/connect", response_model=BrokerConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_broker(
    payload: BrokerConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerConnectResponse:
    account, login_url = broker_readonly_service.connect(db, current_user, payload)
    return BrokerConnectResponse(
        account=broker_account_response(account, login_url=login_url),
        login_url=login_url,
        message="Read-only broker mode connected. Live order placement remains disabled.",
    )


@router.get("/{broker_account_id}/profile", response_model=BrokerProfileResponse)
def get_broker_profile(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerProfileResponse:
    account = require_account(db, current_user, broker_account_id)
    return broker_readonly_call(db, current_user, account, "profile", lambda: broker_readonly_service.get_profile(db, current_user, account))


@router.get("/{broker_account_id}/funds", response_model=BrokerFundsResponse)
def get_broker_funds(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrokerFundsResponse:
    account = require_account(db, current_user, broker_account_id)
    return broker_readonly_call(db, current_user, account, "funds", lambda: broker_readonly_service.get_funds(db, current_user, account))


@router.get("/{broker_account_id}/positions", response_model=list[BrokerPositionResponse])
def get_broker_positions(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BrokerPositionResponse]:
    account = require_account(db, current_user, broker_account_id)
    return broker_readonly_call(db, current_user, account, "positions", lambda: broker_readonly_service.get_positions(db, current_user, account))


@router.get("/{broker_account_id}/orders", response_model=list[BrokerOrderStatusResponse])
def get_broker_orders(
    broker_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BrokerOrderStatusResponse]:
    account = require_account(db, current_user, broker_account_id)
    return broker_readonly_call(db, current_user, account, "orders", lambda: broker_readonly_service.get_orders(db, current_user, account))


def require_account(db: Session, current_user: User, broker_account_id: str) -> BrokerAccount:
    try:
        return broker_readonly_service.get_account(db, current_user, broker_account_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BrokerNotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc


def broker_readonly_call(db: Session, current_user: User, account: BrokerAccount, action: str, call):
    try:
        return call()
    except Exception as exc:
        alert_service.create_alert(
            db,
            user_id=current_user.id,
            alert_type="broker_connection_error",
            severity="WARN",
            title="Broker connection error",
            message=f"Read-only broker {action} request failed.",
            entity_type="broker_account",
            entity_id=account.id,
        )
        broker_readonly_service.audit(
            db,
            user_id=current_user.id,
            event_type="broker.connection_error",
            broker_account_id=account.id,
            message=f"Read-only broker {action} request failed",
            payload={"broker_name": account.broker_name, "error": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Broker read-only request failed.") from exc


def broker_account_response(account: BrokerAccount, login_url: str | None = None) -> BrokerAccountResponse:
    return BrokerAccountResponse(
        id=account.id,
        broker_name=account.broker_name,
        display_name=account.display_name,
        is_active=account.is_active,
        is_paper=account.is_paper,
        static_ip_verified=account.static_ip_verified,
        token_expires_at=account.token_expires_at,
        login_url=login_url,
        status="read_only_connected" if account.is_active else "inactive",
    )
