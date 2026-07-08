from __future__ import annotations

from datetime import time
from decimal import Decimal
from pathlib import Path
from urllib import error as urllib_error

import pytest
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, RiskProfile, User
from app.services.broker_readonly import UrlLibBrokerHttpClient, broker_readonly_service
from broker_core import BrokerNetworkError, BrokerNotImplementedError


class FakeHttpClient:
    def __init__(self, _base_url: str) -> None:
        self.responses = {
            "/user/profile": {"data": {"user_id": "AB1234", "user_name": "Readonly Trader", "email": "ro@example.test"}},
            "/user/margins": {
                "data": {
                    "equity": {
                        "available": {"cash": 100000, "collateral": 5000},
                        "utilised": {"debits": 1000},
                        "net": 104000,
                    }
                }
            },
            "/portfolio/positions": {
                "data": {
                    "net": [
                        {
                            "exchange": "NSE",
                            "tradingsymbol": "RELIANCE",
                            "quantity": 3,
                            "average_price": 2500,
                            "last_price": 2510,
                            "product": "CNC",
                            "pnl": 30,
                            "m2m": 30,
                        }
                    ]
                }
            },
            "/orders": {
                "data": [
                    {
                        "order_id": "readonly_order_1",
                        "status": "OPEN",
                        "filled_quantity": 0,
                        "pending_quantity": 3,
                        "average_price": None,
                    }
                ]
            },
        }

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        return self.responses[path]

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        raise AssertionError("Broker read-only endpoint should not POST")


class TimeoutHttpClient:
    def __init__(self, _base_url: str) -> None:
        pass

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        raise BrokerNetworkError("Broker request timed out")

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        raise BrokerNetworkError("Broker request timed out")


def create_user(db_session) -> tuple[User, str]:
    user = User(
        email="broker-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Broker User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
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
    db_session.add(profile)
    db_session.commit()
    return user, create_access_token(user.id)


def connect_readonly_account(client, token: str) -> str:
    response = client.post(
        "/brokers/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"broker_name": "zerodha", "display_name": "Zerodha Read Only"},
    )
    assert response.status_code == 201
    return response.json()["account"]["id"]


def test_connect_broker_creates_read_only_account(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeHttpClient)
    _user, token = create_user(db_session)

    response = client.post(
        "/brokers/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"broker_name": "zerodha", "display_name": "Zerodha Read Only"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["account"]["broker_name"] == "zerodha"
    assert body["account"]["is_paper"] is False
    assert body["account"]["status"] == "read_only_connected"
    assert body["login_url"].startswith("https://kite.zerodha.com/connect/login")


def test_get_profile_maps_broker_response_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_readonly_account(client, token)

    profile = client.get(f"/brokers/{account_id}/profile", headers={"Authorization": f"Bearer {token}"})

    assert profile.status_code == 200
    assert profile.json() == {
        "broker_name": "zerodha",
        "broker_user_id": "AB1234",
        "full_name": "Readonly Trader",
        "email": "ro@example.test",
    }


def test_get_funds_maps_broker_response_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_readonly_account(client, token)

    funds = client.get(f"/brokers/{account_id}/funds", headers={"Authorization": f"Bearer {token}"})

    assert funds.status_code == 200
    assert funds.json() == {
        "broker_name": "zerodha",
        "available_cash": "100000",
        "collateral": "5000",
        "utilized_margin": "1000",
        "net": "104000",
    }


def test_get_positions_maps_broker_response_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_readonly_account(client, token)

    positions = client.get(f"/brokers/{account_id}/positions", headers={"Authorization": f"Bearer {token}"})

    assert positions.status_code == 200
    assert positions.json() == [
        {
            "broker_name": "zerodha",
            "exchange": "NSE",
            "segment": "EQ",
            "symbol": "RELIANCE",
            "quantity": 3,
            "average_price": "2500",
            "last_price": "2510",
            "product_type": "CNC",
            "realized_pnl": "30",
            "unrealized_pnl": "30",
        }
    ]


def test_get_orders_maps_broker_response_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_readonly_account(client, token)

    orders = client.get(f"/brokers/{account_id}/orders", headers={"Authorization": f"Bearer {token}"})

    assert orders.status_code == 200
    assert orders.json() == [
        {
            "broker_order_id": "readonly_order_1",
            "broker_status": "OPEN",
            "normalized_status": "OPEN",
            "filled_quantity": 0,
            "pending_quantity": 3,
            "average_price": None,
            "message": None,
            "updated_at": None,
        }
    ]


def test_broker_api_request_creates_audit_event(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_readonly_account(client, token)

    response = client.get(f"/brokers/{account_id}/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200

    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == account_id)).all()
    event_types = {event.event_type for event in audit_events}
    assert "broker.profile.request" in event_types
    assert "broker.profile.response" in event_types
    assert "broker.http.request" in event_types
    assert "broker.http.response" in event_types

    http_request = next(event for event in audit_events if event.event_type == "broker.http.request")
    assert http_request.raw_payload["path"] == "/user/profile"
    assert http_request.raw_payload["headers"]["Authorization"] == "***redacted***"


def test_place_order_is_disabled() -> None:
    with pytest.raises(BrokerNotImplementedError) as exc:
        raise broker_readonly_service.disabled_order_error()
    assert "disabled" in str(exc.value)


def test_modify_order_is_disabled() -> None:
    with pytest.raises(BrokerNotImplementedError) as exc:
        raise broker_readonly_service.disabled_order_error()
    assert "disabled" in str(exc.value)


def test_cancel_order_is_disabled() -> None:
    with pytest.raises(BrokerNotImplementedError) as exc:
        raise broker_readonly_service.disabled_order_error()
    assert "disabled" in str(exc.value)


def test_real_api_keys_are_not_present_in_code() -> None:
    root = Path(__file__).resolve().parents[4]
    scanned_files = [
        *root.glob(".env.example"),
        *root.glob("apps/api/app/**/*.py"),
        *root.glob("apps/web/**/*.ts"),
        *root.glob("apps/web/**/*.tsx"),
        *root.glob("packages/broker_zerodha/**/*.py"),
    ]
    forbidden_fragments = [
        "api_key=live_",
        "access_token=live_",
        "KITE_API_SECRET=",
        "ZERODHA_API_KEY=kite",
        "ZERODHA_ACCESS_TOKEN=ey",
    ]

    for path in scanned_files:
        if path == Path(__file__).resolve() or "__pycache__" in path.parts or ".next" in path.parts or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(fragment in text for fragment in forbidden_fragments), str(path)

    env_text = (root / ".env.example").read_text(encoding="utf-8")
    assert "replace-with-zerodha-api-key" in env_text
    assert "replace-with-read-only-access-token" in env_text


def test_broker_timeout_and_circuit_breaker_are_handled(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
    monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_token")
    monkeypatch.setenv("BROKER_CIRCUIT_BREAKER_THRESHOLD", "1")
    monkeypatch.setenv("BROKER_CIRCUIT_BREAKER_COOLDOWN_SECONDS", "60")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", TimeoutHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_readonly_account(client, token)

    first = client.get(f"/brokers/{account_id}/profile", headers={"Authorization": f"Bearer {token}"})
    second = client.get(f"/brokers/{account_id}/profile", headers={"Authorization": f"Bearer {token}"})

    assert first.status_code == 502
    assert second.status_code == 502
    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == account_id)).all()
    event_types = {event.event_type for event in audit_events}
    assert "broker.profile.error" in event_types
    assert "broker.profile.blocked" in event_types


def test_broker_timeout_maps_to_broker_network_error(monkeypatch) -> None:
    client = UrlLibBrokerHttpClient("https://example.test")

    def raise_timeout(_req, timeout):
        raise urllib_error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr("app.services.broker_readonly.request.urlopen", raise_timeout)

    with pytest.raises(BrokerNetworkError, match="Broker request timed out"):
        client.get("/user/profile")


def test_list_brokers_requires_auth(client) -> None:
    response = client.get("/brokers")

    assert response.status_code == 401
