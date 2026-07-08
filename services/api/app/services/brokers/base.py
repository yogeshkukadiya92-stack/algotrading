from dataclasses import dataclass
from typing import Protocol

from app.core.enums import OrderStatus
from app.services.risk_engine import OrderIntentSnapshot


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str | None
    status: OrderStatus
    raw_response: dict


class BrokerAdapter(Protocol):
    name: str

    def place_order(self, intent: OrderIntentSnapshot) -> BrokerOrderResult:
        """Place exactly one broker order. Callers must not auto-retry this method."""

