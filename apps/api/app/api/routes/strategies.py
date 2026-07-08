from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.strategies import (
    SignalResponse,
    StrategyActionResponse,
    StrategyCreateRequest,
    StrategyResponse,
)
from app.services.strategy_engine import strategy_engine_service

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy(
    payload: StrategyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StrategyResponse:
    try:
        return StrategyResponse.model_validate(strategy_engine_service.create_strategy(db, current_user, payload))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[StrategyResponse])
def list_strategies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StrategyResponse]:
    return [StrategyResponse.model_validate(strategy) for strategy in strategy_engine_service.list_strategies(db, current_user)]


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StrategyResponse:
    try:
        return StrategyResponse.model_validate(strategy_engine_service.get_strategy(db, current_user, strategy_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{strategy_id}/start", response_model=StrategyActionResponse)
def start_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StrategyActionResponse:
    try:
        strategy, signal = strategy_engine_service.start_strategy(db, current_user, strategy_id)
    except ValueError as exc:
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if "LIVE" in str(exc) or "Paper broker" in str(exc) or "Stopped strategy" in str(exc) or "Kill switch" in str(exc)
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return StrategyActionResponse(
        strategy=StrategyResponse.model_validate(strategy),
        signal=SignalResponse.model_validate(signal) if signal else None,
        message="Paper strategy started",
    )


@router.post("/{strategy_id}/stop", response_model=StrategyActionResponse)
def stop_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StrategyActionResponse:
    try:
        strategy = strategy_engine_service.stop_strategy(db, current_user, strategy_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return StrategyActionResponse(
        strategy=StrategyResponse.model_validate(strategy),
        signal=None,
        message="Paper strategy stopped",
    )


@router.get("/{strategy_id}/signals", response_model=list[SignalResponse])
def list_strategy_signals(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SignalResponse]:
    try:
        return [SignalResponse.model_validate(signal) for signal in strategy_engine_service.list_signals(db, current_user, strategy_id)]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
