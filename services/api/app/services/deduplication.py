import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from app.services.risk_engine import OrderIntentSnapshot


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return str(value)


class DuplicateOrderGuard:
    @staticmethod
    def build_idempotency_key(intent: OrderIntentSnapshot, trade_date: str | None = None) -> str:
        if not intent.client_order_key:
            raise ValueError("client_order_key is required for duplicate order prevention")

        payload = asdict(intent)
        payload["trade_date"] = trade_date or datetime.now(UTC).date().isoformat()
        canonical = json.dumps(payload, sort_keys=True, default=_json_default)
        return hashlib.sha256(canonical.encode()).hexdigest()

