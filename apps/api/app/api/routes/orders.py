from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Position, User
from app.schemas.orders import (
    OrderActionResponse,
    OrderCreateRequest,
    OrderDetailResponse,
    OrderModifyRequest,
    PositionResponse,
)
from app.services.order_management import (
    DuplicateCorrelationError,
    DuplicateOrderRequestError,
    IdempotencyConflictError,
    order_management_service,
)

router = APIRouter(prefix="/orders", tags=["orders"])
positions_router = APIRouter(prefix="/positions", tags=["positions"])


@router.post("", response_model=OrderActionResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderActionResponse:
    try:
        order = order_management_service.create_order(
            db,
            current_user,
            payload,
            idempotency_key=idempotency_key,
            request_id=getattr(request.state, "request_id", None),
        )
    except DuplicateCorrelationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (DuplicateOrderRequestError, IdempotencyConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return OrderActionResponse(order=OrderDetailResponse.model_validate(order), message=order.status)


@router.get("", response_model=list[OrderDetailResponse])
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderDetailResponse]:
    return [OrderDetailResponse.model_validate(order) for order in order_management_service.list_orders(db, current_user)]


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderDetailResponse:
    try:
        return OrderDetailResponse.model_validate(order_management_service.get_order(db, current_user, order_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{order_id}/cancel", response_model=OrderActionResponse)
def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderActionResponse:
    try:
        order = order_management_service.cancel_order(db, current_user, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return OrderActionResponse(order=OrderDetailResponse.model_validate(order), message=order.status)


@router.post("/{order_id}/modify", response_model=OrderActionResponse)
def modify_order(
    order_id: str,
    payload: OrderModifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderActionResponse:
    try:
        order = order_management_service.modify_order(db, current_user, order_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return OrderActionResponse(order=OrderDetailResponse.model_validate(order), message=order.status)


@positions_router.get("", response_model=list[PositionResponse])
def list_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PositionResponse]:
    positions = db.scalars(
        select(Position).where(Position.user_id == current_user.id).order_by(Position.updated_at.desc())
    ).all()
    return [PositionResponse.model_validate(position) for position in positions]
