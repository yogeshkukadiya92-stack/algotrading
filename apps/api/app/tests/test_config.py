from app.core.config import get_settings


def test_live_trading_enabled_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv("LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("ENABLE_LIVE_BROKER_ORDERS", raising=False)

    settings = get_settings()

    assert settings.live_trading_enabled is False


def test_enable_live_broker_orders_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv("LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("ENABLE_LIVE_BROKER_ORDERS", raising=False)

    settings = get_settings()

    assert settings.enable_live_broker_orders is False


def test_auto_trading_enabled_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv("AUTO_TRADING_ENABLED", raising=False)

    settings = get_settings()

    assert settings.auto_trading_enabled is False


def test_enable_auto_trading_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_AUTO_TRADING", raising=False)

    settings = get_settings()

    assert settings.enable_auto_trading is False


def test_paper_trading_defaults_to_true(monkeypatch) -> None:
    monkeypatch.delenv("PAPER_TRADING", raising=False)

    settings = get_settings()

    assert settings.paper_trading is True
