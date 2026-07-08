from fastapi import APIRouter

from app.core.config import get_settings
from app.api.routes.market import market_data_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tradepilot-api",
    }


@router.get("/health/details")
def health_details() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "tradepilot-api",
        "environment": settings.app_env,
        "dependencies": {
            "database_configured": bool(settings.database_url),
            "redis_configured": bool(settings.redis_url),
            "market_data": market_data_service.connection_status(),
        },
        "safety": {
            "live_trading_enabled": settings.live_trading_enabled,
            "enable_live_broker_orders": settings.enable_live_broker_orders,
            "enable_auto_trading": settings.enable_auto_trading,
            "auto_trading_enabled": settings.auto_trading_enabled,
            "paper_trading": settings.paper_trading,
        },
    }
