from app.api.routes.market import market_data_service


def test_watchlist_returns_mock_ticks(client) -> None:
    response = client.get("/market/watchlist")

    assert response.status_code == 200
    body = response.json()
    assert {tick["symbol"] for tick in body} == {
        "NIFTY",
        "BANKNIFTY",
        "NIFTY26JUL24800CE",
        "NIFTY26JUL24800PE",
    }
    assert {"symbol", "exchange", "segment", "ltp", "bid", "ask", "volume", "oi", "timestamp"} <= set(body[0])


def test_quote_returns_single_symbol(client) -> None:
    response = client.get("/market/quote/NIFTY")

    assert response.status_code == 200
    assert response.json()["symbol"] == "NIFTY"


def test_quote_unknown_symbol_returns_404(client) -> None:
    response = client.get("/market/quote/UNKNOWN")

    assert response.status_code == 404


def test_candles_return_one_minute_ohlcv(client) -> None:
    market_data_service.reset()
    client.get("/market/quote/NIFTY")
    client.get("/market/quote/NIFTY")

    response = client.get("/market/candles/NIFTY")

    assert response.status_code == 200
    candle = response.json()[0]
    assert candle["symbol"] == "NIFTY"
    assert {"open", "high", "low", "close", "volume", "start_time"} <= set(candle)
    assert candle["volume"] > 0


def test_market_stream_sends_mock_ticks(client) -> None:
    with client.websocket_connect("/market/stream") as websocket:
        ticks = websocket.receive_json()

    assert len(ticks) == 4
    assert {tick["symbol"] for tick in ticks} == {
        "NIFTY",
        "BANKNIFTY",
        "NIFTY26JUL24800CE",
        "NIFTY26JUL24800PE",
    }


def test_market_endpoints_allow_local_frontend_origin(client) -> None:
    response = client.options(
        "/market/watchlist",
        headers={
            "Origin": "http://127.0.0.1:3012",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3012"


def test_market_data_service_tracks_reconnect_state() -> None:
    market_data_service.reset()
    market_data_service.mark_disconnect("mock disconnect")

    status = market_data_service.connection_status()

    assert status["connected"] is False
    assert status["reconnect_attempts"] == 1
    assert status["last_disconnect_reason"] == "mock disconnect"

    market_data_service.mark_reconnected()
    assert market_data_service.connection_status()["connected"] is True
