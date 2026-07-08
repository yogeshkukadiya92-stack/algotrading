from fastapi import APIRouter, Query

router = APIRouter(prefix="/market", tags=["market-data"])


@router.get("/quotes")
def quotes() -> dict:
    return {
        "source": "delayed-demo-feed",
        "quotes": [
            {"symbol": "NIFTY", "exchange": "NSE", "last_price": 24842.15, "change_pct": 0.42},
            {"symbol": "BANKNIFTY", "exchange": "NSE", "last_price": 52418.8, "change_pct": -0.18},
            {"symbol": "RELIANCE", "exchange": "NSE", "last_price": 3012.4, "change_pct": 0.31},
            {"symbol": "TCS", "exchange": "NSE", "last_price": 4172.0, "change_pct": 0.12},
        ],
    }


@router.get("/option-chain")
def option_chain(underlying: str = Query(default="NIFTY"), spot: float = Query(default=24842.15)) -> dict:
    step = 50 if underlying.upper() == "NIFTY" else 100
    base = round(spot / step) * step
    strikes = [base + (i * step) for i in range(-5, 6)]
    chain = []
    for strike in strikes:
        distance = abs(strike - spot)
        intrinsic_call = max(spot - strike, 0)
        intrinsic_put = max(strike - spot, 0)
        time_value = max(12, 120 - distance * 0.9)
        chain.append(
            {
                "strike": strike,
                "call": {
                    "ltp": round(intrinsic_call + time_value, 2),
                    "oi": int(120000 - distance * 800),
                    "iv": round(11.5 + distance / 1000, 2),
                },
                "put": {
                    "ltp": round(intrinsic_put + time_value, 2),
                    "oi": int(118000 - distance * 760),
                    "iv": round(12.1 + distance / 950, 2),
                },
            }
        )
    return {"underlying": underlying.upper(), "spot": spot, "expiry": "nearest-weekly", "chain": chain}

