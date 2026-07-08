import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.backtests import router as backtests_router
from app.api.routes.brokers import router as brokers_router
from app.api.routes.controls import router as controls_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.market import router as market_router
from app.api.routes.options import router as options_router
from app.api.routes.orders import router as orders_router
from app.api.routes.risk import router as risk_router
from app.api.routes.strategies import router as strategies_router
from app.core.config import get_settings
from app.core.errors import build_error_response, register_exception_handlers
from app.core.logging import configure_logging, log_json
from app.services.rate_limit import rate_limiter

configure_logging()
logger = logging.getLogger("tradepilot.apps.api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TradePilot India API",
        version="0.1.0",
        description="Minimal FastAPI backend scaffold for TradePilot India.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id") or f"req_{uuid4().hex}"
        request.state.request_id = request_id
        request.state.correlation_id = request_id
        request.state.started_at = perf_counter()

        client_host = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "anonymous"
        )
        rate_limit_key = f"{client_host}:{request.method}:{request.url.path}"
        allowed, retry_after = rate_limiter.allow(
            rate_limit_key,
            limit=get_settings().rate_limit_per_minute,
            window_seconds=get_settings().rate_limit_window_seconds,
        )
        if not allowed:
            response = build_error_response(
                request,
                status_code=429,
                detail="Rate limit exceeded",
                error_code="rate_limit_exceeded",
            )
            response.headers["retry-after"] = str(retry_after)
            log_json(
                logger,
                "http.rate_limited",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client_host=client_host,
                retry_after=retry_after,
            )
            return response

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-correlation-id"] = request_id
        log_json(
            logger,
            "http.request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((perf_counter() - request.state.started_at) * 1000, 2),
        )
        return response

    app.include_router(auth_router)
    app.include_router(alerts_router)
    app.include_router(backtests_router)
    app.include_router(brokers_router)
    app.include_router(controls_router)
    app.include_router(health_router)
    app.include_router(logs_router)
    app.include_router(market_router)
    app.include_router(options_router)
    app.include_router(orders_router)
    app.include_router(risk_router)
    app.include_router(strategies_router)
    return app


app = create_app()
