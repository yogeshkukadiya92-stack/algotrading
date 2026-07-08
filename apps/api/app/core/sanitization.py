from __future__ import annotations

import re
from typing import Any

SECRET_FRAGMENTS = ("api_key", "apikey", "access_token", "token", "secret", "authorization", "password")
SECRET_VALUE = "***redacted***"
KEY_VALUE_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|token|secret|password)\s*=\s*([^\s,;]+)"),
    re.compile(r"(?i)\b(authorization)\s*:\s*([^\s,;]+(?:\s+[^\s,;]+)?)"),
]
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+")


def mask_sensitive_data(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _mask_value(str(key), value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [mask_sensitive_data(item) for item in payload]
    if isinstance(payload, tuple):
        return [mask_sensitive_data(item) for item in payload]
    if isinstance(payload, str):
        return mask_sensitive_string(payload)
    return payload


def mask_sensitive_string(value: str) -> str:
    lowered = value.lower()
    if any(fragment in lowered for fragment in SECRET_FRAGMENTS):
        masked = value
        for pattern in KEY_VALUE_PATTERNS:
            masked = pattern.sub(lambda match: f"{match.group(1)}={SECRET_VALUE}", masked)
        masked = BEARER_PATTERN.sub(f"Bearer {SECRET_VALUE}", masked)
        if masked != value:
            return masked
        return SECRET_VALUE
    return value


def _mask_value(key: str, value: Any) -> Any:
    if any(fragment in key.lower() for fragment in SECRET_FRAGMENTS):
        return SECRET_VALUE
    return mask_sensitive_data(value)
