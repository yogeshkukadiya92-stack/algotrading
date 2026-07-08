import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent


def _safe_json(data: Any) -> Any:
    return json.loads(json.dumps(data, default=str))


class AuditWriter:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        event_type: str,
        correlation_id: str,
        user_id: str | None = None,
        broker_account_id: str | None = None,
        payload: dict | None = None,
        request: dict | None = None,
        response: dict | None = None,
        success: bool = True,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            correlation_id=correlation_id,
            user_id=user_id,
            broker_account_id=broker_account_id,
            payload=_safe_json(payload or {}),
            request=_safe_json(request) if request is not None else None,
            response=_safe_json(response) if response is not None else None,
            success=success,
        )
        self.db.add(event)
        return event

