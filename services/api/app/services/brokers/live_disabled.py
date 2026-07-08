from app.services.brokers.base import BrokerOrderResult
from app.services.risk_engine import OrderIntentSnapshot


class LiveTradingDisabledError(RuntimeError):
    pass


class LiveDisabledBrokerAdapter:
    name = "live-disabled"

    def place_order(self, intent: OrderIntentSnapshot) -> BrokerOrderResult:
        raise LiveTradingDisabledError("No live broker adapter is configured")

