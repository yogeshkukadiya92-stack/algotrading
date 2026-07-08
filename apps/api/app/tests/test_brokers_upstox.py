from __future__ import annotations

from datetime import time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import AuditEvent, RiskProfile, User
from app.services.broker_readonly import broker_readonly_service


class FakeUpstoxHttpClient:
    def __init__(self, _base_url: str) -> None:
        self.responses = {
            "/v2/user/profile": {
                "status": "success",
                "data": {
                    "user_id": "UPX123",
                    "first_name": "Upstox",
                    "last_name": "Reader",
                    "email": "upstox-reader@example.test",
                },
            },
            "/v2/user/get-funds-and-margin": {
                "status": "success",
                "data": {
                    "equity": {
                        "available_margin": 125000,
                        "collateral": 15000,
                        "used_margin": 3200,
                        "net": 136800,
                    }
                },
            },
            "/v2/portfolio/short-term-positions": {
                "status": "success",
                "data": [
                    {
                        "exchange": "NSE",
                        "trading_symbol": "RELIANCE",
                        "quantity": 4,
                        "average_price": 2950,
                        "last_price": 2965,
                        "product_type": "CNC",
                        "realized_pnl": 40,
                        "unrealized_pnl": 60,
                    }
                ],
            },
            "/v2/order/retrieve-all": {
                "status": "success",
                "data": [
                    {
                        "order_id": "upstox_readonly_order_1",
                        "status": "OPEN",
                        "filled_quantity": 0,
                        "pending_quantity": 4,
                        "average_price": None,
                    }
                ],
            },
        }

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        return self.responses[path]

    def post(self, path: str, data: dict | None = None, headers: dict[str, str] | None = None) -> dict:
        raise AssertionError("Read-only Upstox tests should not post broker orders")


def create_user(db_session) -> tuple[User, str]:
    user = User(
        email="upstox-broker-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Upstox Broker User",
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


def connect_upstox_account(client, token: str) -> str:
    response = client.post(
        "/brokers/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"broker_name": "upstox", "display_name": "Upstox Read Only"},
    )
    assert response.status_code == 201
    return response.json()["account"]["id"]


def test_connect_upstox_creates_read_only_account(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_KEY", "fake_upstox_key")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeUpstoxHttpClient)
    _user, token = create_user(db_session)

    response = client.post(
        "/brokers/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"broker_name": "upstox", "display_name": "Upstox Read Only"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["account"]["broker_name"] == "upstox"
    assert body["account"]["status"] == "read_only_connected"
    assert body["login_url"].startswith("https://api.upstox.com/v2/login/authorization/dialog")


def test_upstox_profile_maps_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_KEY", "fake_upstox_key")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "fake_upstox_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeUpstoxHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_upstox_account(client, token)

    response = client.get(f"/brokers/{account_id}/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "broker_name": "upstox",
        "broker_user_id": "UPX123",
        "full_name": "Upstox Reader",
        "email": "upstox-reader@example.test",
    }


def test_upstox_funds_map_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_KEY", "fake_upstox_key")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "fake_upstox_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeUpstoxHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_upstox_account(client, token)

    response = client.get(f"/brokers/{account_id}/funds", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "broker_name": "upstox",
        "available_cash": "125000",
        "collateral": "15000",
        "utilized_margin": "3200",
        "net": "136800",
    }


def test_upstox_positions_map_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_KEY", "fake_upstox_key")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "fake_upstox_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeUpstoxHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_upstox_account(client, token)

    response = client.get(f"/brokers/{account_id}/positions", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "broker_name": "upstox",
            "exchange": "NSE",
            "segment": "EQ",
            "symbol": "RELIANCE",
            "quantity": 4,
            "average_price": "2950",
            "last_price": "2965",
            "product_type": "CNC",
            "realized_pnl": "40",
            "unrealized_pnl": "60",
        }
    ]


def test_upstox_orders_map_correctly(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_KEY", "fake_upstox_key")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "fake_upstox_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeUpstoxHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_upstox_account(client, token)

    response = client.get(f"/brokers/{account_id}/orders", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "broker_order_id": "upstox_readonly_order_1",
            "broker_status": "OPEN",
            "normalized_status": "OPEN",
            "filled_quantity": 0,
            "pending_quantity": 4,
            "average_price": None,
            "message": None,
            "updated_at": None,
        }
    ]


def test_upstox_broker_api_request_creates_audit_event(client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_KEY", "fake_upstox_key")
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "fake_upstox_token")
    monkeypatch.setattr(broker_readonly_service, "http_client_factory", FakeUpstoxHttpClient)
    _user, token = create_user(db_session)
    account_id = connect_upstox_account(client, token)

    response = client.get(f"/brokers/{account_id}/profile", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_id == account_id)).all()
    event_types = {event.event_type for event in audit_events}
    assert "broker.profile.request" in event_types
    assert "broker.profile.response" in event_types
    assert "broker.http.request" in event_types
    assert "broker.http.response" in event_types

    request_event = next(event for event in audit_events if event.event_type == "broker.http.request")
    assert request_event.raw_payload["path"] == "/v2/user/profile"
    assert request_event.raw_payload["headers"]["Authorization"] == "***redacted***"


def test_upstox_real_api_keys_are_not_present_in_code() -> None:
    root = Path(__file__).resolve().parents[4]
    scanned_files = [
        *root.glob(".env.example"),
        *root.glob("apps/api/app/**/*.py"),
        *root.glob("packages/broker_upstox/**/*.py"),
    ]
    forbidden_fragments = [
        "UPSTOX_API_KEY=live_",
        "UPSTOX_ACCESS_TOKEN=ey",
        "Authorization: Bearer live_",
    ]

    for path in scanned_files:
        if path == Path(__file__).resolve() or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(fragment in text for fragment in forbidden_fragments), str(path)
