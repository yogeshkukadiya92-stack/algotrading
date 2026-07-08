import pytest

from app.services.deduplication import DuplicateOrderGuard
from tests.test_risk_engine import make_intent


def test_same_order_intent_produces_same_idempotency_key() -> None:
    first = DuplicateOrderGuard.build_idempotency_key(make_intent(), trade_date="2026-07-08")
    second = DuplicateOrderGuard.build_idempotency_key(make_intent(), trade_date="2026-07-08")

    assert first == second


def test_client_order_key_changes_idempotency_key() -> None:
    first = DuplicateOrderGuard.build_idempotency_key(make_intent(), trade_date="2026-07-08")
    second = DuplicateOrderGuard.build_idempotency_key(
        make_intent(client_order_key="client_order_002"), trade_date="2026-07-08"
    )

    assert first != second


def test_client_order_key_is_required() -> None:
    with pytest.raises(ValueError, match="client_order_key is required"):
        DuplicateOrderGuard.build_idempotency_key(
            make_intent(client_order_key=""), trade_date="2026-07-08"
        )

