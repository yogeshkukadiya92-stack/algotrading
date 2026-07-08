from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BrokerAccount, RiskProfile, User
from app.schemas.orders import OrderCreateRequest, OrderSource, OrderType, TradingMode
from app.services.system_controls import KillSwitchActiveError, system_control_service

LIVE_ORDER_CONFIRMATION_TEXT = "CONFIRM LIVE ORDER"


@dataclass(frozen=True)
class LiveTradingDecision:
    approved: bool
    rule: str
    reason: str


class LiveTradingGuard:
    def evaluate(
        self,
        db: Session,
        *,
        user: User,
        broker_account: BrokerAccount,
        risk_profile: RiskProfile | None,
        payload: OrderCreateRequest,
    ) -> LiveTradingDecision:
        if payload.mode != TradingMode.LIVE:
            return LiveTradingDecision(True, "paper_order", "Paper order does not require live trading guard.")

        settings = get_settings()
        if not settings.enable_live_broker_orders:
            return LiveTradingDecision(False, "live_broker_orders_disabled", "Live broker order routing is disabled.")

        try:
            system_control_service.ensure_orders_allowed(db, user)
        except KillSwitchActiveError as exc:
            return LiveTradingDecision(False, "kill_switch_enabled", str(exc))

        if not user.live_trading_enabled:
            return LiveTradingDecision(False, "user_live_trading_disabled", "User has not enabled live trading.")

        if risk_profile is None or not risk_profile.allow_live_trading:
            return LiveTradingDecision(
                False,
                "risk_profile_live_trading_disabled",
                "Risk profile does not allow live trading.",
            )

        if not broker_account.static_ip_verified:
            return LiveTradingDecision(False, "static_ip_not_verified", "Broker account static IP is not verified.")

        if payload.source != OrderSource.MANUAL:
            return LiveTradingDecision(False, "manual_live_only", "Only manual live orders are allowed.")

        if payload.order_type not in {OrderType.LIMIT, OrderType.SL_LIMIT}:
            return LiveTradingDecision(False, "live_order_type_not_allowed", "Only LIVE LIMIT and SL_LIMIT orders are allowed.")

        if payload.confirmation_text != LIVE_ORDER_CONFIRMATION_TEXT and not payload.confirmation_token:
            return LiveTradingDecision(
                False,
                "live_order_confirmation_missing",
                "Live order confirmation text is required.",
            )

        return LiveTradingDecision(True, "live_order_guard_approved", "Live order guard approved.")


live_trading_guard = LiveTradingGuard()
