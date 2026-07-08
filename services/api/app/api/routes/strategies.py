from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.strategies import StrategySignalCreate, StrategySignalResponse
from app.services.audit import AuditWriter

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/templates")
def templates() -> dict:
    return {
        "templates": [
            {
                "id": "orb-paper-v1",
                "name": "Opening Range Breakout",
                "mode": "paper-only",
                "emits": "signals",
            },
            {
                "id": "ma-cross-paper-v1",
                "name": "Moving Average Crossover",
                "mode": "paper-only",
                "emits": "signals",
            },
        ]
    }


@router.post("/signals", response_model=StrategySignalResponse)
def emit_signal(
    payload: StrategySignalCreate, db: Session = Depends(get_db)
) -> StrategySignalResponse:
    AuditWriter(db).record(
        "strategy.signal.emitted",
        payload.correlation_id,
        payload.user_id,
        None,
        payload=payload.model_dump(mode="json"),
    )
    db.commit()
    return StrategySignalResponse(
        accepted=True,
        message="Signal accepted. Strategy engine does not place broker orders directly.",
        signal=payload,
    )

