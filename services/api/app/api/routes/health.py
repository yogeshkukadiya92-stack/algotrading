from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "tradepilot-api",
        "environment": settings.environment,
        "live_trading_enabled": settings.live_trading_enabled,
    }

