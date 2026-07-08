from enum import StrEnum


class TradingMode(StrEnum):
    PAPER = "paper"
    LIVE = "live"


class OrderSource(StrEnum):
    MANUAL = "manual"
    ALGO = "algo"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    SL = "sl"
    SLM = "slm"


class TransactionSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    RECEIVED = "received"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    FILLED = "filled"
    CANCELLED = "cancelled"


class Exchange(StrEnum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    BFO = "BFO"


class ProductType(StrEnum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"

