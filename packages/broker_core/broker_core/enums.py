from enum import StrEnum


class BrokerName(StrEnum):
    PAPER = "paper"
    UPSTOX = "upstox"
    DHAN = "dhan"
    ZERODHA = "zerodha"


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    BFO = "BFO"
    CDS = "CDS"
    MCX = "MCX"


class Segment(StrEnum):
    EQ = "EQ"
    FNO = "FNO"
    CURRENCY = "CURRENCY"
    COMMODITY = "COMMODITY"


class TransactionType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL_LIMIT = "SL_LIMIT"
    SL_MARKET = "SL_MARKET"


class ProductType(StrEnum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"


class NormalizedOrderStatus(StrEnum):
    CREATED = "CREATED"
    RECEIVED = "RECEIVED"
    ACCEPTED = "ACCEPTED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    TRIGGER_PENDING = "TRIGGER_PENDING"


class TradingMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class OrderSource(StrEnum):
    MANUAL = "manual"
    API = "api"
    ALGO = "algo"
    STRATEGY = "strategy"
    WEBHOOK = "webhook"
    SYSTEM = "system"
