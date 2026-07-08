from market_data_service import MockMarketDataService


def test_mock_service_generates_expected_watchlist_symbols() -> None:
    service = MockMarketDataService()

    ticks = service.get_watchlist()

    assert {tick.symbol for tick in ticks} == {
        "NIFTY",
        "BANKNIFTY",
        "NIFTY26JUL24800CE",
        "NIFTY26JUL24800PE",
    }


def test_mock_service_builds_one_minute_candles() -> None:
    service = MockMarketDataService()
    service.generate_tick("NIFTY")
    service.generate_tick("NIFTY")

    candles = service.get_candles("NIFTY")

    assert candles is not None
    assert candles[0].symbol == "NIFTY"
    assert candles[0].high >= candles[0].low
    assert candles[0].volume > 0
