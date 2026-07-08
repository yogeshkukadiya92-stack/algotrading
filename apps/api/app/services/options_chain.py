from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib import error as urllib_error
from urllib import parse, request

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.sanitization import mask_sensitive_data
from app.models import AuditEvent
from app.schemas.options import OptionChainResponse, OptionChainSource, OptionStrikeResponse
from app.services.broker_resilience import CircuitBreakerOpenError, broker_circuit_breaker


class BrokerOptionChainError(Exception):
    pass


class MockOptionChainService:
    _underlyings = {
        "NIFTY": {
            "spot": Decimal("24820.35"),
            "step": Decimal("50"),
            "width": 7,
            "base_oi": 120000,
            "base_volume": 18000,
        },
        "BANKNIFTY": {
            "spot": Decimal("53240.70"),
            "step": Decimal("100"),
            "width": 7,
            "base_oi": 85000,
            "base_volume": 12500,
        },
    }

    def get_chain(self, underlying: str = "NIFTY", expiry: str = "2026-07-30") -> OptionChainResponse:
        normalized_underlying = underlying.upper()
        if normalized_underlying not in self._underlyings:
            raise ValueError("Unsupported underlying")

        config = self._underlyings[normalized_underlying]
        spot = config["spot"]
        step = config["step"]
        atm = self._round_to_step(spot, step)
        width = int(config["width"])

        strikes: list[OptionStrikeResponse] = []
        for index in range(-width, width + 1):
            strike = atm + (step * index)
            distance_steps = abs(index)
            distance_value = abs(spot - strike)
            intrinsic_call = max(Decimal("0"), spot - strike)
            intrinsic_put = max(Decimal("0"), strike - spot)
            time_value = max(Decimal("8"), Decimal("120") - (Decimal(distance_steps) * Decimal("13.5")))
            volatility_boost = Decimal("1") + (Decimal(distance_steps) * Decimal("0.035"))

            ce_ltp = self._money(intrinsic_call + time_value)
            pe_ltp = self._money(intrinsic_put + time_value)
            ce_delta = self._decimal(max(Decimal("0.05"), Decimal("0.52") - (Decimal(index) * Decimal("0.065"))), "0.001")
            pe_delta = self._decimal(min(Decimal("-0.05"), Decimal("-0.48") - (Decimal(index) * Decimal("0.065"))), "0.001")
            gamma = self._decimal(max(Decimal("0.002"), Decimal("0.019") - (Decimal(distance_steps) * Decimal("0.0017"))), "0.0001")
            vega = self._decimal(max(Decimal("1.2"), Decimal("8.5") - (Decimal(distance_steps) * Decimal("0.55"))), "0.01")
            theta = self._decimal(Decimal("-4.5") - (Decimal(distance_steps) * Decimal("0.25")), "0.01")
            iv = self._decimal((Decimal("12.8") * volatility_boost) + (distance_value / spot), "0.01")

            call_wall_bias = max(0, index) * 3200
            put_wall_bias = max(0, -index) * 3000
            oi_fade = max(0, 16000 - (distance_steps * 1800))
            volume_fade = max(0, 5000 - (distance_steps * 550))

            strikes.append(
                OptionStrikeResponse(
                    strike_price=self._money(strike),
                    ce_ltp=ce_ltp,
                    ce_bid=self._money(ce_ltp - Decimal("0.35")),
                    ce_ask=self._money(ce_ltp + Decimal("0.35")),
                    ce_oi=int(config["base_oi"]) + oi_fade + call_wall_bias,
                    ce_volume=int(config["base_volume"]) + volume_fade + (max(0, index) * 850),
                    ce_iv=iv,
                    ce_delta=ce_delta,
                    ce_gamma=gamma,
                    ce_theta=theta,
                    ce_vega=vega,
                    pe_ltp=pe_ltp,
                    pe_bid=self._money(pe_ltp - Decimal("0.35")),
                    pe_ask=self._money(pe_ltp + Decimal("0.35")),
                    pe_oi=int(config["base_oi"]) + oi_fade + put_wall_bias,
                    pe_volume=int(config["base_volume"]) + volume_fade + (max(0, -index) * 825),
                    pe_iv=iv + Decimal("0.25"),
                    pe_delta=pe_delta,
                    pe_gamma=gamma,
                    pe_theta=theta - Decimal("0.15"),
                    pe_vega=vega,
                )
            )

        return OptionChainResponse(
            underlying=normalized_underlying,
            spot_price=self._money(spot),
            expiry=expiry,
            source=OptionChainSource.MOCK,
            strikes=strikes,
        )

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        return (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step

    def _money(self, value: Decimal) -> Decimal:
        return self._decimal(max(Decimal("0.05"), value), "0.05")

    def _decimal(self, value: Decimal, quantum: str) -> Decimal:
        return value.quantize(Decimal(quantum), rounding=ROUND_HALF_UP)


class ZerodhaOptionChainHttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, headers: dict[str, str]) -> dict:
        req = request.Request(f"{self.base_url}{path}", headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=get_settings().broker_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise BrokerOptionChainError("Broker option chain request timed out") from exc
        except urllib_error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError | socket.timeout):
                raise BrokerOptionChainError("Broker option chain request timed out") from exc
            raise BrokerOptionChainError("Broker option chain request failed") from exc


class OptionChainService:
    def __init__(self, *, mock_service: MockOptionChainService | None = None, cache_ttl_seconds: int = 30) -> None:
        self.mock_service = mock_service or MockOptionChainService()
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.cache: dict[tuple[str, str], tuple[datetime, OptionChainResponse]] = {}
        self.http_client_factory = lambda base_url: ZerodhaOptionChainHttpClient(base_url)

    def get_chain(self, db: Session, underlying: str = "NIFTY", expiry: str = "2026-07-30") -> OptionChainResponse:
        normalized_underlying = underlying.upper()
        cache_key = (normalized_underlying, expiry)
        cached = self.cache.get(cache_key)
        if cached and cached[0] > datetime.now(timezone.utc):
            return cached[1]

        if not self._has_broker_credentials():
            return self._mock_with_reason(normalized_underlying, expiry, "Broker credentials missing. Showing mock option chain.")

        try:
            chain = self._get_broker_chain(db, normalized_underlying, expiry)
        except Exception as exc:
            reason = f"Broker option chain unavailable. Showing mock data instead."
            self._audit(
                db,
                event_type="broker.option_chain.fallback",
                message=reason,
                payload={"broker_name": "zerodha", "underlying": normalized_underlying, "expiry": expiry, "error": str(exc)},
            )
            db.commit()
            return self._mock_with_reason(normalized_underlying, expiry, reason)

        self.cache[cache_key] = (datetime.now(timezone.utc) + self.cache_ttl, chain)
        return chain

    def _get_broker_chain(self, db: Session, underlying: str, expiry: str) -> OptionChainResponse:
        base_url = os.getenv("ZERODHA_API_BASE_URL", "https://api.kite.trade")
        path_template = os.getenv("ZERODHA_OPTION_CHAIN_PATH", "/option-chain")
        query = parse.urlencode({"underlying": underlying, "expiry": expiry})
        path = f"{path_template}?{query}"
        breaker_key = f"option_chain:{underlying}:{expiry}"
        headers = self._headers()
        self._audit(
            db,
            event_type="broker.option_chain.request",
            message="Broker option chain request",
            payload={
                "broker_name": "zerodha",
                "method": "GET",
                "path": path,
                "headers": headers,
                "circuit_breaker": broker_circuit_breaker.snapshot(breaker_key),
            },
        )
        try:
            raw = broker_circuit_breaker.protect(
                breaker_key,
                lambda: self.http_client_factory(base_url).get(path, headers=headers),
            )
        except CircuitBreakerOpenError as exc:
            raise BrokerOptionChainError(str(exc)) from exc
        self._audit(
            db,
            event_type="broker.option_chain.response",
            message="Broker option chain response",
            payload={"broker_name": "zerodha", "method": "GET", "path": path, "metadata": self._response_metadata(raw)},
        )
        db.commit()
        return self._normalize_broker_response(raw, underlying, expiry)

    def _normalize_broker_response(self, raw: dict, underlying: str, expiry: str) -> OptionChainResponse:
        data = raw.get("data", raw)
        strikes_raw = data.get("strikes") or data.get("option_chain") or data.get("records") or []
        if not isinstance(strikes_raw, list) or not strikes_raw:
            raise BrokerOptionChainError("Broker response did not include option chain strikes")

        strikes = [self._normalize_strike(item) for item in strikes_raw]
        return OptionChainResponse(
            underlying=str(data.get("underlying", underlying)).upper(),
            spot_price=self._decimal_value(data.get("spot_price", data.get("last_price", data.get("underlying_value", 0)))),
            expiry=str(data.get("expiry", expiry)),
            source=OptionChainSource.BROKER,
            fallback_reason=None,
            strikes=strikes,
        )

    def _normalize_strike(self, item: dict) -> OptionStrikeResponse:
        ce = item.get("ce") or item.get("CE") or {}
        pe = item.get("pe") or item.get("PE") or {}
        return OptionStrikeResponse(
            strike_price=self._decimal_value(item.get("strike_price", item.get("strikePrice"))),
            ce_ltp=self._decimal_value(item.get("ce_ltp", ce.get("ltp", ce.get("last_price", ce.get("lastPrice", 0))))),
            ce_bid=self._decimal_value(item.get("ce_bid", ce.get("bid", ce.get("bid_price", 0)))),
            ce_ask=self._decimal_value(item.get("ce_ask", ce.get("ask", ce.get("ask_price", 0)))),
            ce_oi=int(item.get("ce_oi", ce.get("oi", ce.get("open_interest", 0))) or 0),
            ce_volume=int(item.get("ce_volume", ce.get("volume", 0)) or 0),
            ce_iv=self._decimal_value(item.get("ce_iv", ce.get("iv", 0))),
            ce_delta=self._decimal_value(item.get("ce_delta", ce.get("delta", 0))),
            ce_gamma=self._decimal_value(item.get("ce_gamma", ce.get("gamma", 0))),
            ce_theta=self._decimal_value(item.get("ce_theta", ce.get("theta", 0))),
            ce_vega=self._decimal_value(item.get("ce_vega", ce.get("vega", 0))),
            pe_ltp=self._decimal_value(item.get("pe_ltp", pe.get("ltp", pe.get("last_price", pe.get("lastPrice", 0))))),
            pe_bid=self._decimal_value(item.get("pe_bid", pe.get("bid", pe.get("bid_price", 0)))),
            pe_ask=self._decimal_value(item.get("pe_ask", pe.get("ask", pe.get("ask_price", 0)))),
            pe_oi=int(item.get("pe_oi", pe.get("oi", pe.get("open_interest", 0))) or 0),
            pe_volume=int(item.get("pe_volume", pe.get("volume", 0)) or 0),
            pe_iv=self._decimal_value(item.get("pe_iv", pe.get("iv", 0))),
            pe_delta=self._decimal_value(item.get("pe_delta", pe.get("delta", 0))),
            pe_gamma=self._decimal_value(item.get("pe_gamma", pe.get("gamma", 0))),
            pe_theta=self._decimal_value(item.get("pe_theta", pe.get("theta", 0))),
            pe_vega=self._decimal_value(item.get("pe_vega", pe.get("vega", 0))),
        )

    def _mock_with_reason(self, underlying: str, expiry: str, reason: str) -> OptionChainResponse:
        chain = self.mock_service.get_chain(underlying=underlying, expiry=expiry)
        chain.source = OptionChainSource.MOCK
        chain.fallback_reason = reason
        return chain

    def _has_broker_credentials(self) -> bool:
        api_key = os.getenv("ZERODHA_API_KEY", "")
        access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")
        return bool(api_key and access_token and not api_key.startswith("replace-") and not access_token.startswith("replace-"))

    def _headers(self) -> dict[str, str]:
        api_key = os.getenv("ZERODHA_API_KEY", "")
        access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")
        return {"X-Kite-Version": "3", "Authorization": f"token {api_key}:{access_token}"}

    def _audit(self, db: Session, *, event_type: str, message: str, payload: dict[str, Any]) -> None:
        db.add(
            AuditEvent(
                user_id=None,
                event_type=event_type,
                entity_type="option_chain",
                entity_id=None,
                message=message,
                raw_payload=self._redact(payload),
            )
        )

    def _response_metadata(self, raw: dict) -> dict[str, Any]:
        data = raw.get("data", raw)
        strikes = data.get("strikes") or data.get("option_chain") or data.get("records") or []
        return {
            "status": raw.get("status"),
            "underlying": data.get("underlying"),
            "expiry": data.get("expiry"),
            "strike_count": len(strikes) if isinstance(strikes, list) else 0,
        }

    def _redact(self, value: Any) -> Any:
        return mask_sensitive_data(value)

    def _decimal_value(self, value: object) -> Decimal:
        return Decimal(str(value or "0"))


option_chain_service = OptionChainService()
