from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.backtests import BacktestCreateRequest, BacktestRunResponse
from app.services.backtesting import backtesting_service

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED)
def create_backtest(
    payload: BacktestCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BacktestRunResponse:
    try:
        return BacktestRunResponse.model_validate(backtesting_service.create_backtest(db, current_user, payload))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[BacktestRunResponse])
def list_backtests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BacktestRunResponse]:
    return [BacktestRunResponse.model_validate(run) for run in backtesting_service.list_backtests(db, current_user)]


@router.get("/{backtest_id}", response_model=BacktestRunResponse)
def get_backtest(
    backtest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BacktestRunResponse:
    try:
        return BacktestRunResponse.model_validate(backtesting_service.get_backtest(db, current_user, backtest_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
