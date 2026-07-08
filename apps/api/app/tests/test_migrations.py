from __future__ import annotations

import importlib.util
import os
import subprocess
from datetime import time
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models import BrokerAccount, Order, RiskProfile, User


def _load_demo_seed_module():
    root = Path(__file__).resolve().parents[4]
    module_path = root / "db" / "seed" / "demo_seed.py"
    spec = importlib.util.spec_from_file_location("demo_seed", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load demo seed module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alembic_migration_runs_successfully(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "migration.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    api_root = Path(__file__).resolve().parents[2]
    workspace_root = Path(__file__).resolve().parents[4]
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(api_root)
    subprocess.run(
        [
            str(api_root / ".venv" / "bin" / "python"),
            "-c",
            (
                "from alembic.config import Config; "
                "from alembic import command; "
                "cfg = Config(r'%s'); "
                "cfg.set_main_option('script_location', r'%s'); "
                "cfg.set_main_option('sqlalchemy.url', r'%s'); "
                "command.upgrade(cfg, 'head')"
                % (str(api_root / "alembic.ini"), str(api_root / "alembic"), database_url)
            ),
        ],
        cwd=workspace_root,
        env=env,
        check=True,
    )

    engine = create_engine(database_url)
    table_names = set(inspect(engine).get_table_names())
    assert "alembic_version" in table_names
    assert "users" in table_names
    assert "orders" in table_names
    assert "risk_profiles" in table_names
    order_indexes = {index["name"] for index in inspect(engine).get_indexes("orders")}
    assert {"ix_orders_user_id", "ix_orders_correlation_id", "ix_orders_created_at"} <= order_indexes


def test_required_hardening_indexes_exist() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert {"ix_orders_user_id", "ix_orders_correlation_id", "ix_orders_created_at"} <= {
        index["name"] for index in inspector.get_indexes("orders")
    }
    assert "ix_order_events_order_id" in {index["name"] for index in inspector.get_indexes("order_events")}
    assert {"ix_audit_events_user_id", "ix_audit_events_created_at"} <= {
        index["name"] for index in inspector.get_indexes("audit_events")
    }
    assert "ix_signals_strategy_id" in {index["name"] for index in inspector.get_indexes("signals")}


def test_model_defaults_persist_as_false() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    user = User(
        email="defaults@tradepilot.in",
        hashed_password="hash",
        full_name="Defaults User",
    )
    session.add(user)
    session.flush()

    profile = RiskProfile(
        user_id=user.id,
        max_daily_loss=1000,
        max_order_value=50000,
        max_lots_per_order=2,
        max_trades_per_day=5,
        max_open_positions=3,
        allowed_start_time=time(hour=9, minute=15),
        allowed_end_time=time(hour=15, minute=20),
        auto_square_off_time=time(hour=15, minute=25),
    )
    session.add(profile)
    session.flush()

    assert user.live_trading_enabled is False
    assert user.auto_trading_enabled is False
    assert profile.allow_live_trading is False
    assert profile.allow_auto_trading is False

    session.close()


def test_order_correlation_id_is_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    user = User(email="orders@tradepilot.in", hashed_password="hash", full_name="Orders User")
    session.add(user)
    session.flush()

    broker_account = BrokerAccount(
        user_id=user.id,
        broker_name="paper",
        display_name="Paper Broker",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
    )
    session.add(broker_account)
    session.flush()

    first_order = Order(
        correlation_id="corr_123",
        user_id=user.id,
        broker_account_id=broker_account.id,
        broker_name="paper",
        symbol="RELIANCE",
        exchange="NSE",
        segment="EQ",
        transaction_type="BUY",
        product_type="MIS",
        order_type="LIMIT",
        quantity=10,
        price=3000,
        status="received",
        risk_status="pending",
        source="manual",
        mode="paper",
    )
    session.add(first_order)
    session.commit()

    duplicate_order = Order(
        correlation_id="corr_123",
        user_id=user.id,
        broker_account_id=broker_account.id,
        broker_name="paper",
        symbol="TCS",
        exchange="NSE",
        segment="EQ",
        transaction_type="BUY",
        product_type="MIS",
        order_type="LIMIT",
        quantity=5,
        price=4000,
        status="received",
        risk_status="pending",
        source="manual",
        mode="paper",
    )
    session.add(duplicate_order)

    try:
        session.commit()
        raise AssertionError("Expected unique constraint failure for duplicate correlation_id")
    except IntegrityError:
        session.rollback()
    finally:
        session.close()


def test_demo_seed_creates_user_and_default_risk_profile() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    demo_seed = _load_demo_seed_module()

    demo_seed.seed_demo_data(session_factory=SessionLocal)

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "demo@tradepilot.in"))
        assert user is not None
        assert user.live_trading_enabled is False
        assert user.auto_trading_enabled is False

        profile = session.scalar(select(RiskProfile).where(RiskProfile.user_id == user.id))
        assert profile is not None
        assert profile.allow_live_trading is False
        assert profile.allow_auto_trading is False
