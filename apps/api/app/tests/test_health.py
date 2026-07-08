def test_health_endpoint_returns_expected_payload(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "tradepilot-api",
    }


def test_health_details_reports_safe_defaults(client) -> None:
    response = client.get("/health/details")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "tradepilot-api"
    assert body["safety"]["live_trading_enabled"] is False
    assert body["safety"]["enable_live_broker_orders"] is False
    assert body["safety"]["enable_auto_trading"] is False
    assert body["safety"]["auto_trading_enabled"] is False
    assert body["safety"]["paper_trading"] is True
