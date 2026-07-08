from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from random import Random

from market_data_service.models import CandleDTO, TickDTO


class MockMarketDataService:
    def __init__(self, seed: int = 42) -> None:
        self._random = Random(seed)
        self._instruments = {
            "NIFTY": {"exchange": "NSE", "segment": "INDEX", "base": Decimal("24800"), "spread": Decimal("0.50")},
            "BANKNIFTY": {"exchange": "NSE", "segment": "INDEX", "base": Decimal("53200"), "spread": Decimal("1.00")},
            "NIFTY26JUL24800CE": {"exchange": "NFO", "segment": "OPTIDX", "base": Decimal("142.50"), "spread": Decimal("0.10")},
            "NIFTY26JUL24800PE": {"exchange": "NFO", "segment": "OPTIDX", "base": Decimal("128.75"), "spread": Decimal("0.10")},
        }
        self._latest_ticks: dict[str, TickDTO] = {}
        self._candles: dict[str, list[CandleDTO]] = {symbol: [] for symbol in self._instruments}
        self._step = 0
        self._connected = True
        self._reconnect_attempts = 0
        self._last_disconnect_reason: str | None = None
        self._last_disconnect_at: datetime | None = None
        self.bootstrap()

    @property
    def symbols(self) -> list[str]:
        return list(self._instruments)

    def reset(self) -> None:
        self._latest_ticks.clear()
        self._candles = {symbol: [] for symbol in self._instruments}
        self._step = 0
        self._connected = True
        self._reconnect_attempts = 0
        self._last_disconnect_reason = None
        self._last_disconnect_at = None
        self.bootstrap()

    def mark_disconnect(self, reason: str) -> None:
        self._connected = False
        self._reconnect_attempts += 1
        self._last_disconnect_reason = reason
        self._last_disconnect_at = datetime.now(timezone.utc)

    def mark_reconnected(self) -> None:
        self._connected = True

    def connection_status(self) -> dict[str, object]:
        return {
            "connected": self._connected,
            "reconnect_attempts": self._reconnect_attempts,
            "last_disconnect_reason": self._last_disconnect_reason,
            "last_disconnect_at": self._last_disconnect_at,
        }

    def bootstrap(self) -> None:
        for symbol in self._instruments:
            self.generate_tick(symbol)

    def get_watchlist(self) -> list[TickDTO]:
        self.generate_all_ticks()
        return [self._latest_ticks[symbol] for symbol in self.symbols]

    def get_quote(self, symbol: str) -> TickDTO | None:
        normalized_symbol = symbol.upper()
        if normalized_symbol not in self._instruments:
            return None
        return self.generate_tick(normalized_symbol)

    def get_candles(self, symbol: str) -> list[CandleDTO] | None:
        normalized_symbol = symbol.upper()
        if normalized_symbol not in self._instruments:
            return None
        if normalized_symbol not in self._latest_ticks:
            self.generate_tick(normalized_symbol)
        return list(self._candles[normalized_symbol])

    def generate_all_ticks(self) -> list[TickDTO]:
        return [self.generate_tick(symbol) for symbol in self.symbols]

    def generate_tick(self, symbol: str) -> TickDTO:
        normalized_symbol = symbol.upper()
        instrument = self._instruments[normalized_symbol]
        previous_tick = self._latest_ticks.get(normalized_symbol)
        previous_ltp = previous_tick.ltp if previous_tick is not None else instrument["base"]
        drift = Decimal(str(self._random.uniform(-0.35, 0.35))).quantize(Decimal("0.01"))
        if instrument["segment"] == "INDEX":
            drift *= Decimal("8")
        ltp = max(Decimal("0.05"), (previous_ltp + drift).quantize(Decimal("0.05")))
        spread = instrument["spread"]
        now = datetime.now(timezone.utc)
        volume_increment = self._random.randint(50, 500)
        previous_volume = previous_tick.volume if previous_tick is not None else 0
        previous_oi = previous_tick.oi if previous_tick is not None else self._random.randint(100000, 300000)

        tick = TickDTO(
            symbol=normalized_symbol,
            exchange=instrument["exchange"],
            segment=instrument["segment"],
            ltp=ltp,
            bid=(ltp - spread).quantize(Decimal("0.05")),
            ask=(ltp + spread).quantize(Decimal("0.05")),
            volume=previous_volume + volume_increment,
            oi=previous_oi + self._random.randint(-100, 100),
            timestamp=now,
        )
        self._latest_ticks[normalized_symbol] = tick
        self._update_candle(tick, volume_increment)
        self._step += 1
        return tick

    def _update_candle(self, tick: TickDTO, volume_increment: int) -> None:
        start_time = tick.timestamp.replace(second=0, microsecond=0)
        candles = self._candles[tick.symbol]
        if not candles or candles[-1].start_time != start_time:
            candles.append(
                CandleDTO(
                    symbol=tick.symbol,
                    open=tick.ltp,
                    high=tick.ltp,
                    low=tick.ltp,
                    close=tick.ltp,
                    volume=volume_increment,
                    start_time=start_time,
                )
            )
            return

        current = candles[-1]
        candles[-1] = CandleDTO(
            symbol=current.symbol,
            open=current.open,
            high=max(current.high, tick.ltp),
            low=min(current.low, tick.ltp),
            close=tick.ltp,
            volume=current.volume + volume_increment,
            start_time=current.start_time,
        )
