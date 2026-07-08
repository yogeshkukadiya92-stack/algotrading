from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BacktestRun, User
from app.schemas.backtests import BacktestCreateRequest
from app.services.strategy_engine import DemoStrategy, StrategyContext, StrategyInterface


SAMPLE_CANDLE_CSV = """timestamp,symbol,open,high,low,close,volume
2026-07-01T09:15:00,NIFTY,24800,24890,24780,24840,10000
2026-07-01T09:16:00,NIFTY,24840,24930,24810,24910,12000
2026-07-01T09:17:00,NIFTY,24910,24950,24830,24860,11000
2026-07-01T09:18:00,NIFTY,24860,24880,24790,24810,9000
2026-07-01T09:19:00,NIFTY,24810,24920,24795,24895,13000
2026-07-01T09:20:00,NIFTY,24895,24985,24870,24970,14000
2026-07-01T09:21:00,NIFTY,24970,24990,24860,24890,10000
2026-07-01T09:22:00,NIFTY,24890,24910,24800,24820,9500
2026-07-01T09:23:00,NIFTY,24820,24930,24810,24905,12500
2026-07-01T09:24:00,NIFTY,24905,25000,24890,24980,15000
"""


@dataclass(frozen=True)
class HistoricalCandle:
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class BacktestingService:
    def __init__(self) -> None:
        self.strategy_factory = DemoStrategy

    def create_backtest(self, db: Session, user: User, payload: BacktestCreateRequest) -> BacktestRun:
        candles = self._load_sample_candles(payload.symbol, payload.start_date, payload.end_date)
        strategy = self.strategy_factory()
        context = StrategyContext(
            strategy_id="backtest",
            user_id=user.id,
            config={
                "symbol": payload.symbol.upper(),
                "quantity": payload.quantity,
                "stop_loss_points": str(payload.stop_loss_points),
                "target_points": str(payload.target_points),
                "mode": "paper",
            },
        )
        trades = self._run_demo_strategy(candles, payload, strategy, context)
        metrics = self._calculate_metrics(trades, payload.initial_capital)
        result = {
            **metrics,
            "trades": trades,
            "data_source": "sample_csv",
            "warning": "Backtest results do not guarantee future returns.",
        }
        run = BacktestRun(
            user_id=user.id,
            strategy_name=payload.strategy_name,
            strategy_version=payload.strategy_version,
            symbol=payload.symbol.upper(),
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_capital=payload.initial_capital,
            total_trades=metrics["total_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            win_rate=metrics["win_rate"],
            net_pnl=metrics["net_pnl"],
            max_drawdown=metrics["max_drawdown"],
            config={
                "quantity": payload.quantity,
                "stop_loss_points": str(payload.stop_loss_points),
                "target_points": str(payload.target_points),
            },
            result=self._jsonify(result),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def list_backtests(self, db: Session, user: User) -> list[BacktestRun]:
        return list(
            db.scalars(
                select(BacktestRun).where(BacktestRun.user_id == user.id).order_by(BacktestRun.created_at.desc())
            ).all()
        )

    def get_backtest(self, db: Session, user: User, backtest_id: str) -> BacktestRun:
        run = db.scalar(select(BacktestRun).where(BacktestRun.id == backtest_id, BacktestRun.user_id == user.id))
        if run is None:
            raise ValueError("Backtest not found")
        return run

    def _load_sample_candles(self, symbol: str, start_date: date, end_date: date) -> list[HistoricalCandle]:
        rows = csv.DictReader(StringIO(SAMPLE_CANDLE_CSV))
        candles: list[HistoricalCandle] = []
        for row in rows:
            timestamp = datetime.fromisoformat(row["timestamp"])
            if row["symbol"].upper() != symbol.upper() or not (start_date <= timestamp.date() <= end_date):
                continue
            candles.append(
                HistoricalCandle(
                    timestamp=timestamp,
                    symbol=row["symbol"].upper(),
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=int(row["volume"]),
                )
            )
        return candles

    def _run_demo_strategy(
        self,
        candles: list[HistoricalCandle],
        payload: BacktestCreateRequest,
        strategy: StrategyInterface,
        context: StrategyContext,
    ) -> list[dict]:
        trades: list[dict] = []
        position: dict | None = None
        for candle in candles:
            strategy.on_candle(
                {
                    "timestamp": candle.timestamp.isoformat(),
                    "symbol": candle.symbol,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                },
                context,
            )
            if position is None:
                if candle.close > candle.open:
                    entry_price = candle.close
                    position = {
                        "entry_time": candle.timestamp,
                        "entry_price": entry_price,
                        "stop_loss": entry_price - payload.stop_loss_points,
                        "target": entry_price + payload.target_points,
                    }
                continue

            exit_price = None
            exit_reason = None
            if candle.low <= position["stop_loss"]:
                exit_price = position["stop_loss"]
                exit_reason = "STOP_LOSS"
            elif candle.high >= position["target"]:
                exit_price = position["target"]
                exit_reason = "TARGET"

            if exit_price is not None:
                pnl = (exit_price - position["entry_price"]) * Decimal(payload.quantity)
                trades.append(
                    {
                        "symbol": payload.symbol.upper(),
                        "side": "BUY",
                        "quantity": payload.quantity,
                        "entry_time": position["entry_time"].isoformat(),
                        "entry_price": position["entry_price"],
                        "exit_time": candle.timestamp.isoformat(),
                        "exit_price": exit_price,
                        "exit_reason": exit_reason,
                        "pnl": pnl,
                    }
                )
                position = None

        if position is not None and candles:
            last = candles[-1]
            pnl = (last.close - position["entry_price"]) * Decimal(payload.quantity)
            trades.append(
                {
                    "symbol": payload.symbol.upper(),
                    "side": "BUY",
                    "quantity": payload.quantity,
                    "entry_time": position["entry_time"].isoformat(),
                    "entry_price": position["entry_price"],
                    "exit_time": last.timestamp.isoformat(),
                    "exit_price": last.close,
                    "exit_reason": "END_OF_DATA",
                    "pnl": pnl,
                }
            )
        return trades

    def _calculate_metrics(self, trades: list[dict], initial_capital: Decimal) -> dict:
        pnls = [Decimal(str(trade["pnl"])) for trade in trades]
        winners = [pnl for pnl in pnls if pnl > 0]
        losers = [pnl for pnl in pnls if pnl < 0]
        total_trades = len(pnls)
        gross_profit = sum(winners, Decimal("0"))
        gross_loss = sum(losers, Decimal("0"))
        net_pnl = gross_profit + gross_loss
        equity = initial_capital
        peak = initial_capital
        max_drawdown = Decimal("0")
        for pnl in pnls:
            equity += pnl
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)

        return {
            "total_trades": total_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": (Decimal(len(winners)) / Decimal(total_trades) * Decimal("100")) if total_trades else Decimal("0"),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_pnl": net_pnl,
            "max_drawdown": max_drawdown,
            "average_profit_per_trade": gross_profit / Decimal(len(winners)) if winners else Decimal("0"),
            "average_loss_per_trade": gross_loss / Decimal(len(losers)) if losers else Decimal("0"),
        }

    def _jsonify(self, value):
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, list):
            return [self._jsonify(item) for item in value]
        if isinstance(value, dict):
            return {key: self._jsonify(item) for key, item in value.items()}
        return value


backtesting_service = BacktestingService()
