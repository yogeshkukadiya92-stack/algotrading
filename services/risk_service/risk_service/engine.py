from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Sequence

from risk_service.models import (
    OrderSource,
    OrderType,
    PositionSnapshot,
    RecentOrderSnapshot,
    RiskDecision,
    RiskOrderRequest,
    RiskProfile,
    RiskSeverity,
    RiskUser,
    TradingMode,
)


class RiskEngine:
    def evaluate_order(
        self,
        order_request: RiskOrderRequest,
        user: RiskUser,
        risk_profile: RiskProfile,
        current_positions: Sequence[PositionSnapshot],
        today_pnl: Decimal,
        recent_orders: Sequence[RecentOrderSnapshot],
    ) -> RiskDecision:
        evaluation_time = (order_request.evaluation_time or datetime.now()).time()

        for decision in (
            self._block_if_user_live_disabled(order_request, user),
            self._block_if_user_auto_disabled(order_request, user),
            self._block_if_profile_live_disabled(order_request, risk_profile),
            self._block_if_market_order(order_request),
            self._block_if_quantity_invalid(order_request),
            self._block_if_max_lots_exceeded(order_request, risk_profile),
            self._block_if_max_order_value_exceeded(order_request, risk_profile),
            self._block_if_daily_loss_reached(risk_profile, today_pnl),
            self._block_if_trade_count_reached(risk_profile, recent_orders),
            self._block_if_open_positions_reached(order_request, risk_profile, current_positions),
            self._block_if_duplicate_correlation(order_request, recent_orders),
            self._block_if_outside_trading_window(risk_profile, evaluation_time),
            self._block_if_static_ip_unverified(order_request),
        ):
            if decision is not None:
                return decision

        return RiskDecision(
            approved=True,
            rule="all_rules_passed",
            reason="Order approved by risk engine",
            severity=RiskSeverity.INFO,
        )

    def _block_if_user_live_disabled(self, order_request: RiskOrderRequest, user: RiskUser) -> RiskDecision | None:
        if order_request.mode == TradingMode.LIVE and not user.live_trading_enabled:
            return self._blocked(
                "user_live_trading_disabled",
                "Live trading is disabled for this user.",
            )
        return None

    def _block_if_user_auto_disabled(self, order_request: RiskOrderRequest, user: RiskUser) -> RiskDecision | None:
        if order_request.source in {OrderSource.AUTO, OrderSource.ALGO, OrderSource.STRATEGY, OrderSource.WEBHOOK}:
            if not user.auto_trading_enabled:
                return self._blocked(
                    "user_auto_trading_disabled",
                    "Auto trading is disabled for this user.",
                )
        return None

    def _block_if_profile_live_disabled(
        self,
        order_request: RiskOrderRequest,
        risk_profile: RiskProfile,
    ) -> RiskDecision | None:
        if order_request.mode == TradingMode.LIVE and not risk_profile.allow_live_trading:
            return self._blocked(
                "risk_profile_live_trading_disabled",
                "Live trading is not enabled in the risk profile.",
            )
        return None

    def _block_if_market_order(self, order_request: RiskOrderRequest) -> RiskDecision | None:
        if order_request.order_type == OrderType.MARKET:
            return self._blocked(
                "market_orders_not_allowed",
                "MARKET orders are not allowed by the risk engine.",
            )
        return None

    def _block_if_quantity_invalid(self, order_request: RiskOrderRequest) -> RiskDecision | None:
        if order_request.quantity <= 0:
            return self._blocked(
                "quantity_must_be_positive",
                "Order quantity must be greater than zero.",
            )
        return None

    def _block_if_max_lots_exceeded(
        self,
        order_request: RiskOrderRequest,
        risk_profile: RiskProfile,
    ) -> RiskDecision | None:
        lots = Decimal(order_request.quantity) / Decimal(order_request.lot_size)
        if lots > Decimal(risk_profile.max_lots_per_order):
            return self._blocked(
                "max_lots_per_order_exceeded",
                "Order exceeds the maximum lots allowed per order.",
            )
        return None

    def _block_if_max_order_value_exceeded(
        self,
        order_request: RiskOrderRequest,
        risk_profile: RiskProfile,
    ) -> RiskDecision | None:
        price_reference = order_request.price or order_request.trigger_price
        if price_reference is None:
            return None

        order_value = Decimal(order_request.quantity) * price_reference
        if order_value > risk_profile.max_order_value:
            return self._blocked(
                "max_order_value_exceeded",
                "Order value exceeds the configured maximum order value.",
            )
        return None

    def _block_if_daily_loss_reached(
        self,
        risk_profile: RiskProfile,
        today_pnl: Decimal,
    ) -> RiskDecision | None:
        if today_pnl <= -abs(risk_profile.max_daily_loss):
            return self._blocked(
                "max_daily_loss_reached",
                "Daily loss limit has been reached for this user.",
            )
        return None

    def _block_if_trade_count_reached(
        self,
        risk_profile: RiskProfile,
        recent_orders: Sequence[RecentOrderSnapshot],
    ) -> RiskDecision | None:
        if len(recent_orders) >= risk_profile.max_trades_per_day:
            return self._blocked(
                "max_trades_per_day_reached",
                "Maximum trades per day has been reached.",
            )
        return None

    def _block_if_open_positions_reached(
        self,
        order_request: RiskOrderRequest,
        risk_profile: RiskProfile,
        current_positions: Sequence[PositionSnapshot],
    ) -> RiskDecision | None:
        open_positions = [position for position in current_positions if position.quantity != 0]
        existing_symbols = {position.symbol for position in open_positions}
        if order_request.symbol not in existing_symbols and len(open_positions) >= risk_profile.max_open_positions:
            return self._blocked(
                "max_open_positions_reached",
                "Maximum open positions limit has been reached.",
            )
        return None

    def _block_if_duplicate_correlation(
        self,
        order_request: RiskOrderRequest,
        recent_orders: Sequence[RecentOrderSnapshot],
    ) -> RiskDecision | None:
        if any(order.correlation_id == order_request.correlation_id for order in recent_orders):
            return self._blocked(
                "duplicate_correlation_id",
                "An order with this correlation_id already exists.",
            )
        return None

    def _block_if_outside_trading_window(
        self,
        risk_profile: RiskProfile,
        evaluation_time,
    ) -> RiskDecision | None:
        if not (risk_profile.allowed_start_time <= evaluation_time <= risk_profile.allowed_end_time):
            return self._blocked(
                "outside_trading_window",
                "Order is outside the allowed trading window.",
            )
        return None

    def _block_if_static_ip_unverified(self, order_request: RiskOrderRequest) -> RiskDecision | None:
        if order_request.mode == TradingMode.LIVE and not order_request.broker_account_static_ip_verified:
            return self._blocked(
                "static_ip_not_verified",
                "Live trading requires a broker account with verified static IP.",
            )
        return None

    def _blocked(self, rule: str, reason: str) -> RiskDecision:
        return RiskDecision(
            approved=False,
            rule=rule,
            reason=reason,
            severity=RiskSeverity.BLOCK,
        )
