from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import RiskProfile
from app.schemas.risk import RiskProfileResponse, RiskProfileUpsert

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/profiles/{user_id}/{broker_account_id}", response_model=RiskProfileResponse)
def get_profile(
    user_id: str, broker_account_id: str, db: Session = Depends(get_db)
) -> RiskProfileResponse:
    profile = db.scalar(
        select(RiskProfile).where(
            RiskProfile.user_id == user_id,
            RiskProfile.broker_account_id == broker_account_id,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Risk profile is not configured")
    return RiskProfileResponse.model_validate(profile)


@router.post("/profiles", response_model=RiskProfileResponse)
def upsert_profile(payload: RiskProfileUpsert, db: Session = Depends(get_db)) -> RiskProfileResponse:
    profile = db.scalar(
        select(RiskProfile).where(
            RiskProfile.user_id == payload.user_id,
            RiskProfile.broker_account_id == payload.broker_account_id,
        )
    )
    if profile is None:
        profile = RiskProfile(user_id=payload.user_id, broker_account_id=payload.broker_account_id)
        db.add(profile)

    profile.is_configured = payload.is_configured
    profile.allow_live_trading = payload.allow_live_trading
    profile.max_order_quantity = payload.max_order_quantity
    profile.max_order_value = payload.max_order_value
    profile.max_day_notional = payload.max_day_notional
    profile.allowed_products = [item.value for item in payload.allowed_products]
    db.commit()
    db.refresh(profile)
    return RiskProfileResponse.model_validate(profile)

