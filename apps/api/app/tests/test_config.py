from app.core.config import get_settings
from pydantic import ValidationError


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


def test_database_url_normalizes_railway_postgres_urls(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db-host:5432/tradepilot")

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://user:pass@db-host:5432/tradepilot"


def test_database_url_rejects_mongodb_urls(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "mongodb://mongo-user:mongo-pass@mongo-host:27017/tradepilot")

    try:
        get_settings()
    except ValidationError as exc:
        assert "PostgreSQL DATABASE_URL" in str(exc)
    else:
        raise AssertionError("Expected MongoDB DATABASE_URL to be rejected")
