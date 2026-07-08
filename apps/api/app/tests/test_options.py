from sqlalchemy import select

from app.models import AuditEvent
from app.services.options_chain import option_chain_service


class FakeOptionChainHttpClient:
    calls = 0
    fail = False

    def __init__(self, _base_url: str) -> None:
        pass

    def get(self, path: str, headers: dict[str, str]) -> dict:
        type(self).calls += 1
        if type(self).fail:
            raise RuntimeError("broker timeout")
        return {
            "status": "success",
            "data": {
                "underlying": "NIFTY",
                "spot_price": 24888.25,
                "expiry": "2026-07-30",
                "strikes": [
                    {
                        "strike_price": 24850,
                        "ce": {
                            "ltp": 155.5,
                            "bid": 155.25,
                            "ask": 155.75,
                            "oi": 12000,
                            "volume": 3400,
                            "iv": 13.2,
                            "delta": 0.58,
                            "gamma": 0.012,
                            "theta": -4.2,
                            "vega": 7.5,
                        },
                        "pe": {
                            "ltp": 115.5,
                            "bid": 115.25,
                            "ask": 115.75,
                            "oi": 13500,
                            "volume": 3900,
                            "iv": 13.6,
                            "delta": -0.42,
                            "gamma": 0.012,
                            "theta": -4.4,
                            "vega": 7.4,
                        },
                    }
                ],
            },
        }


def reset_option_chain_service(monkeypatch, *, has_credentials: bool = False, fail: bool = False) -> None:
    option_chain_service.cache.clear()
    FakeOptionChainHttpClient.calls = 0
    FakeOptionChainHttpClient.fail = fail
    monkeypatch.setattr(option_chain_service, "http_client_factory", FakeOptionChainHttpClient)
    if has_credentials:
        monkeypatch.setenv("ZERODHA_API_KEY", "fake_key")
        monkeypatch.setenv("ZERODHA_ACCESS_TOKEN", "fake_access_token")
    else:
        monkeypatch.delenv("ZERODHA_API_KEY", raising=False)
        monkeypatch.delenv("ZERODHA_ACCESS_TOKEN", raising=False)


def test_option_chain_returns_mock_nifty_chain(client) -> None:
    response = client.get("/options/chain?underlying=NIFTY&expiry=2026-07-30")

    assert response.status_code == 200
    body = response.json()
    assert body["underlying"] == "NIFTY"
    assert body["expiry"] == "2026-07-30"
    assert body["source"] == "MOCK"
    assert float(body["spot_price"]) > 0
    assert len(body["strikes"]) == 15

    strike = body["strikes"][0]
    assert {
        "strike_price",
        "ce_ltp",
        "ce_bid",
        "ce_ask",
        "ce_oi",
        "ce_volume",
        "ce_iv",
        "ce_delta",
        "ce_gamma",
        "ce_theta",
        "ce_vega",
        "pe_ltp",
        "pe_bid",
        "pe_ask",
        "pe_oi",
        "pe_volume",
        "pe_iv",
        "pe_delta",
        "pe_gamma",
        "pe_theta",
        "pe_vega",
    } <= set(strike)


def test_option_chain_supports_banknifty(client) -> None:
    response = client.get("/options/chain?underlying=BANKNIFTY&expiry=2026-07-30")

    assert response.status_code == 200
    body = response.json()
    assert body["underlying"] == "BANKNIFTY"
    assert body["strikes"][1]["strike_price"] != body["strikes"][0]["strike_price"]


def test_option_chain_rejects_unknown_underlying(client) -> None:
    response = client.get("/options/chain?underlying=RELIANCE&expiry=2026-07-30")

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported underlying"


def test_option_chain_falls_back_to_mock_when_credentials_missing(client, monkeypatch) -> None:
    reset_option_chain_service(monkeypatch, has_credentials=False)

    response = client.get("/options/chain?underlying=NIFTY&expiry=2026-07-30")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "MOCK"
    assert "credentials missing" in body["fallback_reason"].lower()
    assert FakeOptionChainHttpClient.calls == 0


def test_option_chain_maps_broker_response_and_audits(client, db_session, monkeypatch) -> None:
    reset_option_chain_service(monkeypatch, has_credentials=True)

    response = client.get("/options/chain?underlying=NIFTY&expiry=2026-07-30")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "BROKER"
    assert body["fallback_reason"] is None
    assert body["spot_price"] == "24888.25"
    assert body["strikes"][0]["strike_price"] == "24850"
    assert body["strikes"][0]["ce_ltp"] == "155.5"
    assert body["strikes"][0]["pe_delta"] == "-0.42"

    audit_events = db_session.scalars(select(AuditEvent).where(AuditEvent.entity_type == "option_chain")).all()
    event_types = {event.event_type for event in audit_events}
    assert "broker.option_chain.request" in event_types
    assert "broker.option_chain.response" in event_types
    request_event = next(event for event in audit_events if event.event_type == "broker.option_chain.request")
    assert request_event.raw_payload["headers"]["Authorization"] == "***redacted***"
    response_event = next(event for event in audit_events if event.event_type == "broker.option_chain.response")
    assert response_event.raw_payload["metadata"]["strike_count"] == 1
    serialized_events = str([event.raw_payload for event in audit_events])
    assert "fake_access_token" not in serialized_events
    assert "fake_key" not in serialized_events


def test_option_chain_uses_short_cache_to_avoid_repeated_broker_calls(client, monkeypatch) -> None:
    reset_option_chain_service(monkeypatch, has_credentials=True)

    first = client.get("/options/chain?underlying=NIFTY&expiry=2026-07-30")
    second = client.get("/options/chain?underlying=NIFTY&expiry=2026-07-30")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["source"] == "BROKER"
    assert second.json()["source"] == "BROKER"
    assert FakeOptionChainHttpClient.calls == 1


def test_option_chain_falls_back_to_mock_when_broker_fails(client, db_session, monkeypatch) -> None:
    reset_option_chain_service(monkeypatch, has_credentials=True, fail=True)

    response = client.get("/options/chain?underlying=NIFTY&expiry=2026-07-30")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "MOCK"
    assert "broker option chain unavailable" in body["fallback_reason"].lower()
    assert "broker timeout" not in body["fallback_reason"].lower()
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.event_type == "broker.option_chain.fallback"))
    assert event is not None
    assert event.raw_payload["error"] == "broker timeout"
