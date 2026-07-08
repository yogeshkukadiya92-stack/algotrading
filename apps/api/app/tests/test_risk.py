from datetime import date, datetime, time
from decimal import Decimal

from app.core.security import create_access_token, hash_password
from app.models import BrokerAccount, Order, PnlSnapshot, RiskProfile, User


def create_authenticated_user(db_session, *, live_trading_enabled=False, auto_trading_enabled=False) -> tuple[User, str]:
    user = User(
        email="risk-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Risk User",
        live_trading_enabled=live_trading_enabled,
        auto_trading_enabled=auto_trading_enabled,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, create_access_token(user.id)


def create_broker_account(db_session, user: User, *, static_ip_verified=False) -> BrokerAccount:
    broker_account = BrokerAccount(
        user_id=user.id,
        broker_name="paper",
        display_name="Risk Broker",
        encrypted_api_key="enc-key",
        encrypted_access_token="enc-token",
        static_ip_verified=static_ip_verified,
    )
    db_session.add(broker_account)
    db_session.commit()
    db_session.refresh(broker_account)
    return broker_account


def create_risk_profile(db_session, user: User, **overrides) -> RiskProfile:
    payload = {
        "user_id": user.id,
        "max_daily_loss": Decimal("5000"),
        "max_order_value": Decimal("100000"),
        "max_lots_per_order": 10,
        "max_trades_per_day": 5,
        "max_open_positions": 5,
        "allowed_start_time": time(9, 15),
        "allowed_end_time": time(15, 20),
        "auto_square_off_time": time(15, 25),
        "allow_live_trading": False,
        "allow_auto_trading": False,
    }
    payload.update(overrides)
    profile = RiskProfile(
        **payload,
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def test_evaluate_order_returns_block_reason_for_market_order(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    broker_account = create_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user)

    response = client.post(
        "/risk/evaluate-order",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "broker_account_id": broker_account.id,
            "correlation_id": "risk_api_market_001",
            "symbol": "RELIANCE",
            "order_type": "MARKET",
            "quantity": 10,
            "source": "manual",
            "mode": "paper",
            "lot_size": 1,
            "evaluation_time": "2026-07-08T10:00:00",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "approved": False,
        "rule": "market_orders_not_allowed",
        "reason": "MARKET orders are not allowed by the risk engine.",
        "severity": "BLOCK",
    }


def test_evaluate_order_blocks_live_order_when_static_ip_is_not_verified(client, db_session) -> None:
    user, token = create_authenticated_user(db_session, live_trading_enabled=True)
    broker_account = create_broker_account(db_session, user, static_ip_verified=False)
    create_risk_profile(db_session, user, allow_live_trading=True)

    response = client.post(
        "/risk/evaluate-order",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "broker_account_id": broker_account.id,
            "correlation_id": "risk_api_live_001",
            "symbol": "RELIANCE",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "2500",
            "source": "manual",
            "mode": "live",
            "lot_size": 1,
            "evaluation_time": "2026-07-08T10:00:00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approved"] is False
    assert body["rule"] == "static_ip_not_verified"
    assert body["severity"] == "BLOCK"


def test_evaluate_order_approves_valid_paper_order(client, db_session) -> None:
    user, token = create_authenticated_user(db_session)
    broker_account = create_broker_account(db_session, user, static_ip_verified=True)
    create_risk_profile(db_session, user)
    db_session.add(
        PnlSnapshot(
            user_id=user.id,
            date=date.today(),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("500"),
            total_pnl=Decimal("500"),
        )
    )
    db_session.add(
        Order(
            correlation_id="older_order_001",
            user_id=user.id,
            broker_account_id=broker_account.id,
            broker_name="paper",
            symbol="TCS",
            exchange="NSE",
            segment="EQ",
            transaction_type="BUY",
            product_type="MIS",
            order_type="LIMIT",
            quantity=1,
            price=Decimal("100"),
            status="received",
            risk_status="approved",
            source="manual",
            mode="paper",
        )
    )
    db_session.commit()

    response = client.post(
        "/risk/evaluate-order",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "broker_account_id": broker_account.id,
            "correlation_id": "risk_api_ok_001",
            "symbol": "RELIANCE",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "2500",
            "source": "manual",
            "mode": "paper",
            "lot_size": 1,
            "evaluation_time": datetime.combine(date.today(), time(10, 0)).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "approved": True,
        "rule": "all_rules_passed",
        "reason": "Order approved by risk engine",
        "severity": "INFO",
    }
