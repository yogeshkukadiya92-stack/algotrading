from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable, TypeVar

from app.core.config import get_settings

T = TypeVar("T")


class CircuitBreakerOpenError(RuntimeError):
    pass


@dataclass
class CircuitBreakerState:
    consecutive_failures: int = 0
    open_until: datetime | None = None


class BrokerCircuitBreaker:
    def __init__(self) -> None:
        self._states: dict[str, CircuitBreakerState] = {}

    def protect(self, key: str, call: Callable[[], T]) -> T:
        self._ensure_closed(key)
        try:
            result = call()
        except Exception:
            self.record_failure(key)
            raise
        self.record_success(key)
        return result

    def record_success(self, key: str) -> None:
        self._states[key] = CircuitBreakerState()

    def record_failure(self, key: str) -> None:
        state = self._states.setdefault(key, CircuitBreakerState())
        state.consecutive_failures += 1
        threshold = get_settings().broker_circuit_breaker_threshold
        if state.consecutive_failures >= threshold:
            cooldown = timedelta(seconds=get_settings().broker_circuit_breaker_cooldown_seconds)
            state.open_until = datetime.now(UTC) + cooldown

    def snapshot(self, key: str) -> dict[str, object]:
        state = self._states.get(key, CircuitBreakerState())
        return {
            "consecutive_failures": state.consecutive_failures,
            "open_until": state.open_until.isoformat() if state.open_until else None,
            "is_open": bool(state.open_until and state.open_until > datetime.now(UTC)),
        }

    def reset(self) -> None:
        self._states.clear()

    def _ensure_closed(self, key: str) -> None:
        state = self._states.get(key)
        if state is None or state.open_until is None:
            return
        if state.open_until <= datetime.now(UTC):
            self._states[key] = CircuitBreakerState()
            return
        raise CircuitBreakerOpenError("Broker API circuit breaker is open")


broker_circuit_breaker = BrokerCircuitBreaker()
