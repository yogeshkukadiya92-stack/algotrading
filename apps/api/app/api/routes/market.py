import asyncio
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

CURRENT_FILE = Path(__file__).resolve()
ROOT_CANDIDATES = [Path.cwd(), *CURRENT_FILE.parents, Path("/")]
for root_candidate in ROOT_CANDIDATES:
    package_path = root_candidate / "services" / "market_data_service"
    if package_path.exists() and str(package_path) not in sys.path:
        sys.path.insert(0, str(package_path))

from market_data_service import CandleDTO, MockMarketDataService, TickDTO  # noqa: E402

router = APIRouter(prefix="/market", tags=["market"])

market_data_service = MockMarketDataService()


@router.get("/watchlist", response_model=list[TickDTO])
def get_watchlist() -> list[TickDTO]:
    return market_data_service.get_watchlist()


@router.get("/quote/{symbol}", response_model=TickDTO)
def get_quote(symbol: str) -> TickDTO:
    tick = market_data_service.get_quote(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return tick


@router.get("/candles/{symbol}", response_model=list[CandleDTO])
def get_candles(symbol: str) -> list[CandleDTO]:
    candles = market_data_service.get_candles(symbol)
    if candles is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return candles


@router.websocket("/stream")
async def stream_market_data(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            try:
                ticks = market_data_service.generate_all_ticks()
                await websocket.send_json([tick.model_dump(mode="json") for tick in ticks])
                market_data_service.mark_reconnected()
            except RuntimeError as exc:
                market_data_service.mark_disconnect(str(exc))
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        market_data_service.mark_disconnect("client disconnected")
        return
