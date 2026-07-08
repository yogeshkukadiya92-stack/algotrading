from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import BacktestRun, Order, User
from app.services.backtesting import backtesting_service
from app.services.order_management import order_management_service


def create_user(db_session) -> tuple[User, str]:
    user = User(
        email="backtest-user@tradepilot.in",
        hashed_password=hash_password("StrongPass123"),
        full_name="Backtest User",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, create_access_token(user.id)


def backtest_payload(**overrides) -> dict:
    payload = {
        "strategy_name": "DemoStrategy",
        "strategy_version": "0.1.0",
        "symbol": "NIFTY",
        "start_date": "2026-07-01",
        "end_date": "2026-07-08",
        "initial_capital": "100000",
        "quantity": 1,
        "stop_loss_points": "40",
        "target_points": "80",
    }
    payload.update(overrides)
    return payload


def test_create_backtest_calculates_metrics_and_trade_list(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["strategy_name"] == "DemoStrategy"
    assert body["symbol"] == "NIFTY"
    assert body["total_trades"] > 0
    assert body["winning_trades"] + body["losing_trades"] <= body["total_trades"]
    assert body["result"]["data_source"] == "sample_csv"
    assert "gross_profit" in body["result"]
    assert "gross_loss" in body["result"]
    assert "average_profit_per_trade" in body["result"]
    assert "average_loss_per_trade" in body["result"]
    assert body["result"]["trades"]
    assert body["result"]["warning"] == "Backtest results do not guarantee future returns."

    stored = db_session.scalar(select(BacktestRun).where(BacktestRun.id == body["id"]))
    assert stored is not None
    assert stored.total_trades == body["total_trades"]


def test_backtest_runs_on_sample_candle_data(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["result"]["data_source"] == "sample_csv"
    assert body["result"]["trades"][0]["entry_time"].startswith("2026-07-01T09:")


def test_strategy_receives_historical_candles(client, db_session, monkeypatch) -> None:
    _user, token = create_user(db_session)
    received_candles = []

    class SpyStrategy:
        name = "DemoStrategy"
        version = "0.1.0"

        def on_start(self, context):
            return None

        def on_tick(self, tick, context):
            return None

        def on_candle(self, candle, context):
            received_candles.append((candle, context))
            return None

        def on_order_update(self, order, context):
            return None

        def on_stop(self, context):
            return None

    monkeypatch.setattr(backtesting_service, "strategy_factory", SpyStrategy)

    response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())

    assert response.status_code == 201
    assert len(received_candles) == 10
    first_candle, context = received_candles[0]
    assert first_candle["symbol"] == "NIFTY"
    assert first_candle["close"] == Decimal("24840")
    assert context.config["mode"] == "paper"


def test_simulated_trades_are_generated(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())

    assert response.status_code == 201
    trade = response.json()["result"]["trades"][0]
    assert trade["symbol"] == "NIFTY"
    assert trade["side"] == "BUY"
    assert trade["exit_reason"] in {"STOP_LOSS", "TARGET", "END_OF_DATA"}
    assert Decimal(trade["pnl"])


def test_pnl_calculation_works(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())

    assert response.status_code == 201
    result = response.json()["result"]
    trade_pnl = sum((Decimal(trade["pnl"]) for trade in result["trades"]), Decimal("0"))
    assert Decimal(result["net_pnl"]) == trade_pnl
    assert Decimal(result["net_pnl"]) == Decimal(result["gross_profit"]) + Decimal(result["gross_loss"])


def test_max_drawdown_calculation_works() -> None:
    metrics = backtesting_service._calculate_metrics(
        [
            {"pnl": Decimal("100")},
            {"pnl": Decimal("-50")},
            {"pnl": Decimal("-25")},
            {"pnl": Decimal("40")},
        ],
        Decimal("1000"),
    )

    assert metrics["max_drawdown"] == Decimal("75")


def test_backtests_can_be_listed_and_fetched(client, db_session) -> None:
    _user, token = create_user(db_session)
    create_response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())
    backtest_id = create_response.json()["id"]

    list_response = client.get("/backtests", headers={"Authorization": f"Bearer {token}"})
    get_response = client.get(f"/backtests/{backtest_id}", headers={"Authorization": f"Bearer {token}"})

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == backtest_id
    assert get_response.status_code == 200
    assert get_response.json()["id"] == backtest_id


def test_backtesting_does_not_create_real_orders_or_call_broker(client, db_session, monkeypatch) -> None:
    _user, token = create_user(db_session)

    def fail_place_order(_order):
        raise AssertionError("Backtesting must not call broker adapters")

    monkeypatch.setattr(order_management_service.paper_adapter, "place_order", fail_place_order)

    response = client.post("/backtests", headers={"Authorization": f"Bearer {token}"}, json=backtest_payload())

    assert response.status_code == 201
    orders = db_session.scalars(select(Order)).all()
    assert orders == []


def test_backtest_rejects_unknown_strategy(client, db_session) -> None:
    _user, token = create_user(db_session)

    response = client.post(
        "/backtests",
        headers={"Authorization": f"Bearer {token}"},
        json=backtest_payload(strategy_name="LiveStrategy"),
    )

    assert response.status_code == 422
    assert "Only DemoStrategy backtests are supported" in str(response.json())


def test_backtesting_service_has_no_broker_or_order_service_imports() -> None:
    service_path = Path(__file__).resolve().parents[1] / "services" / "backtesting.py"
    source = service_path.read_text()

    assert "broker_core" not in source
    assert "BrokerAdapter" not in source
    assert "order_management_service" not in source
    assert "create_order(" not in source


def test_strategies_ui_shows_backtest_risk_disclaimer() -> None:
    page_path = Path(__file__).resolve().parents[3] / "web" / "app" / "(workspace)" / "strategies" / "page.tsx"
    source = page_path.read_text()

    assert "Backtest results do not guarantee future returns." in source
