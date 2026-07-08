from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.options import OptionChainResponse
from app.services.options_chain import option_chain_service

router = APIRouter(prefix="/options", tags=["options"])


@router.get("/chain", response_model=OptionChainResponse)
def get_option_chain(
    underlying: str = Query(default="NIFTY"),
    expiry: str = Query(default="2026-07-30"),
    db: Session = Depends(get_db),
) -> OptionChainResponse:
    try:
        return option_chain_service.get_chain(db=db, underlying=underlying, expiry=expiry)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
