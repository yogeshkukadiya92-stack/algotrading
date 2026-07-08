from uuid import uuid4

from app.core.enums import OrderStatus
from app.services.brokers.base import BrokerOrderResult
from app.services.risk_engine import OrderIntentSnapshot


class PaperBrokerAdapter:
    name = "paper"

    def place_order(self, intent: OrderIntentSnapshot) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker_order_id=f"paper_{uuid4().hex}",
            status=OrderStatus.ACCEPTED,
            raw_response={
                "adapter": self.name,
                "symbol": intent.symbol,
                "exchange": intent.exchange,
                "quantity": intent.quantity,
                "order_type": intent.order_type.value,
                "mode": intent.mode.value,
                "message": "Paper order accepted",
            },
        )

