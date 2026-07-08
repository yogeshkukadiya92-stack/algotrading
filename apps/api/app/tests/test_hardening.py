from __future__ import annotations

import logging
from datetime import time
from decimal import Decimal

from app.core.security import create_access_token, hash_password
from app.models import BrokerAccount, RiskProfile, User


def _create_user_with_account(db_session) -> tuple[User, str, BrokerAccount]:
    user = User(
        email="hardening@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Hardening User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    account = BrokerAccount(
        user_id=user.id,
        broker_name="paper",
        display_name="Paper Hardening",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=True,
    )
    profile = RiskProfile(
        user_id=user.id,
        max_daily_loss=Decimal("5000"),
        max_order_value=Decimal("100000"),
        max_lots_per_order=20,
        max_trades_per_day=20,
        max_open_positions=20,
        allowed_start_time=time(0, 0),
        allowed_end_time=time(23, 59),
        auto_square_off_time=time(15, 25),
    )
    db_session.add_all([account, profile])
    db_session.commit()
    db_session.refresh(account)
    return user, create_access_token(user.id), account


def test_request_id_headers_are_propagated(client) -> None:
    response = client.get("/health", headers={"x-request-id": "req_test_trace_001"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_test_trace_001"
    assert response.headers["x-correlation-id"] == "req_test_trace_001"


def test_request_id_appears_in_logs(client, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="tradepilot.apps.api"):
        response = client.get("/health", headers={"x-request-id": "req_log_trace_001"})

    assert response.status_code == 200
    request_logs = [
        record.msg
        for record in caplog.records
        if record.name == "tradepilot.apps.api" and isinstance(record.msg, dict) and record.msg.get("event") == "http.request"
    ]
    assert request_logs
    assert any(log["request_id"] == "req_log_trace_001" for log in request_logs)


def test_rate_limit_returns_central_error_payload(client, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    first = client.get("/health")
    second = client.get("/health")

    assert first.status_code == 200
    assert second.status_code == 429
    body = second.json()
    assert body["detail"] == "Rate limit exceeded"
    assert body["error_code"] == "rate_limit_exceeded"
    assert second.headers["retry-after"] == "60"
    assert second.headers["x-request-id"] == body["request_id"]


def test_validation_errors_use_central_error_format(client, db_session) -> None:
    _user, token, account = _create_user_with_account(db_session)

    response = client.post(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "broker_account_id": account.id,
            "symbol": "RELIANCE",
            "transaction_type": "BUY",
            "order_type": "LIMIT",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert body["error_code"] == "validation_error"
    assert body["request_id"].startswith("req_")
    assert body["errors"]
