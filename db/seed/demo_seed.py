from __future__ import annotations

import sys
from datetime import time
from decimal import Decimal
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models import BrokerAccount, RiskProfile, User


def seed_demo_data(session_factory: Callable[[], Session] | None = None) -> None:
    factory = session_factory or SessionLocal
    session = factory()
    try:
        existing_user = session.scalar(select(User).where(User.email == "demo@tradepilot.in"))
        if existing_user is None:
            existing_user = User(
                email="demo@tradepilot.in",
                hashed_password=hash_password("DemoPass123"),
                full_name="TradePilot Demo User",
                is_active=True,
                live_trading_enabled=False,
                auto_trading_enabled=False,
            )
            session.add(existing_user)
            session.flush()

        existing_profile = session.scalar(
            select(RiskProfile).where(RiskProfile.user_id == existing_user.id)
        )
        if existing_profile is None:
            session.add(
                RiskProfile(
                    user_id=existing_user.id,
                    max_daily_loss=Decimal("10000"),
                    max_order_value=Decimal("200000"),
                    max_lots_per_order=5,
                    max_trades_per_day=20,
                    max_open_positions=10,
                    allowed_start_time=time(hour=9, minute=15),
                    allowed_end_time=time(hour=15, minute=20),
                    auto_square_off_time=time(hour=15, minute=25),
                    allow_live_trading=False,
                    allow_auto_trading=False,
                )
            )

        existing_account = session.scalar(
            select(BrokerAccount).where(
                BrokerAccount.user_id == existing_user.id,
                BrokerAccount.id == "paper_zerodha_001",
            )
        )
        if existing_account is None:
            session.add(
                BrokerAccount(
                    id="paper_zerodha_001",
                    user_id=existing_user.id,
                    broker_name="paper",
                    display_name="Paper Trading Account",
                    encrypted_api_key="seeded-paper-key",
                    encrypted_access_token="seeded-paper-token",
                    is_active=True,
                    is_paper=True,
                    static_ip_verified=True,
                )
            )

        session.commit()
        print("Seeded demo user, default risk profile, and paper broker account.")
    finally:
        session.close()


if __name__ == "__main__":
    seed_demo_data()
