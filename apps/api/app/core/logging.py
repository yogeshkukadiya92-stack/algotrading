import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.sanitization import mask_sensitive_data


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_sensitive_data(message),
        }
        if isinstance(record.msg, dict):
            payload.update(mask_sensitive_data(record.msg))
        if record.exc_info:
            payload["exception"] = mask_sensitive_data(self.formatException(record.exc_info))
        return json.dumps(mask_sensitive_data(payload), default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def log_json(logger: logging.Logger, event: str, **fields: Any) -> None:
    logger.info({"event": event, **fields})
