from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.orders import OrderIntentCreate, OrderResponse
from app.services.order_service import OrderPlacementService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse)
def place_order(payload: OrderIntentCreate, db: Session = Depends(get_db)) -> OrderResponse:
    order = OrderPlacementService.from_settings().submit(db, payload)
    return OrderResponse.model_validate(order)

