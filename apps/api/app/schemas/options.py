from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class OptionChainSource(StrEnum):
    MOCK = "MOCK"
    BROKER = "BROKER"


class OptionStrikeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strike_price: Decimal
    ce_ltp: Decimal
    ce_bid: Decimal
    ce_ask: Decimal
    ce_oi: int
    ce_volume: int
    ce_iv: Decimal
    ce_delta: Decimal
    ce_gamma: Decimal
    ce_theta: Decimal
    ce_vega: Decimal
    pe_ltp: Decimal
    pe_bid: Decimal
    pe_ask: Decimal
    pe_oi: int
    pe_volume: int
    pe_iv: Decimal
    pe_delta: Decimal
    pe_gamma: Decimal
    pe_theta: Decimal
    pe_vega: Decimal


class OptionChainResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    underlying: str
    spot_price: Decimal
    expiry: str
    source: OptionChainSource = OptionChainSource.MOCK
    fallback_reason: str | None = None
    strikes: list[OptionStrikeResponse]
