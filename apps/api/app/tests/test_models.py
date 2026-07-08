from sqlalchemy import create_engine, inspect

from app.db.base import Base
from app.models import Order, RiskProfile, User


def test_schema_metadata_can_create_all_tables_in_memory() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    Base.metadata.create_all(engine)

    table_names = set(inspect(engine).get_table_names())
    assert table_names == {
        "audit_events",
        "alerts",
        "backtest_runs",
        "broker_accounts",
        "instruments",
        "order_events",
        "orders",
        "pnl_snapshots",
        "positions",
        "risk_profiles",
        "signals",
        "strategies",
        "system_controls",
        "trades",
        "users",
    }


def test_trading_safety_defaults_remain_false() -> None:
    assert User.__table__.c.live_trading_enabled.default.arg is False
    assert User.__table__.c.auto_trading_enabled.default.arg is False
    assert RiskProfile.__table__.c.allow_live_trading.default.arg is False
    assert RiskProfile.__table__.c.allow_auto_trading.default.arg is False
    assert Order.__table__.c.mode.nullable is False
