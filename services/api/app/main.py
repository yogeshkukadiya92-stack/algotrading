import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import brokers, health, market_data, orders, risk, strategies
from app.core.config import get_settings
from app.core.logging import configure_logging, log_json

configure_logging()
logger = logging.getLogger("tradepilot.api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TradePilot India API",
        version="0.1.0",
        description="Paper-first trading backend with risk gates and broker adapter boundaries.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlation_logging(request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id", f"req_{uuid4().hex}")
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        log_json(
            logger,
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            correlation_id=correlation_id,
        )
        return response

    app.include_router(health.router)
    app.include_router(orders.router)
    app.include_router(risk.router)
    app.include_router(brokers.router)
    app.include_router(market_data.router)
    app.include_router(strategies.router)
    return app


app = create_app()

