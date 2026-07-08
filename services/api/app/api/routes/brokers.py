from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import CredentialCipher
from app.db.session import get_db
from app.models import BrokerCredential
from app.schemas.brokers import BrokerCredentialCreate, BrokerCredentialResponse

router = APIRouter(prefix="/brokers", tags=["brokers"])


@router.post("/credentials", response_model=BrokerCredentialResponse)
def save_credentials(
    payload: BrokerCredentialCreate, db: Session = Depends(get_db)
) -> BrokerCredentialResponse:
    try:
        cipher = CredentialCipher()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    credential = db.scalar(
        select(BrokerCredential).where(
            BrokerCredential.broker_account_id == payload.broker_account_id,
            BrokerCredential.broker_name == payload.broker_name,
        )
    )
    if credential is None:
        credential = BrokerCredential(
            user_id=payload.user_id,
            broker_account_id=payload.broker_account_id,
            broker_name=payload.broker_name,
            encrypted_api_key="",
            encrypted_api_secret="",
        )
        db.add(credential)

    credential.encrypted_api_key = cipher.encrypt(payload.api_key)
    credential.encrypted_api_secret = cipher.encrypt(payload.api_secret)
    credential.is_active = True
    db.commit()
    db.refresh(credential)

    return BrokerCredentialResponse(
        id=credential.id,
        user_id=credential.user_id,
        broker_account_id=credential.broker_account_id,
        broker_name=credential.broker_name,
        is_active=credential.is_active,
    )

