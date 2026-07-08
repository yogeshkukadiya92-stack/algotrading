from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BrokerAccount, Order, RiskProfile, Signal, Strategy, User
from app.schemas.orders import OrderCreateRequest, OrderType
from app.services.system_controls import KillSwitchActiveError, system_control_service


@dataclass(frozen=True)
class AutoTradingDecision:
    approved: bool
    rule: str
    reason: str


class AutoTradingGuard:
    def evaluate(
        self,
        db: Session,
        *,
        user: User,
        broker_account: BrokerAccount,
        risk_profile: RiskProfile | None,
        strategy: Strategy | None,
        payload: OrderCreateRequest,
        recent_strategy_orders: list[Order],
        recent_strategy_signals: list[Signal],
        strategy_open_positions: int,
        strategy_pnl: Decimal,
        signal_uid: str,
    ) -> AutoTradingDecision:
        settings = get_settings()
        if not settings.enable_live_broker_orders:
            return self._blocked("live_broker_orders_disabled", "Live broker order routing is disabled.")
        if not settings.enable_auto_trading:
            return self._blocked("auto_trading_env_disabled", "Live auto trading is disabled by environment.")

        try:
            system_control_service.ensure_orders_allowed(db, user)
        except KillSwitchActiveError as exc:
            return self._blocked("kill_switch_enabled", str(exc))

        if not user.live_trading_enabled:
            return self._blocked("user_live_trading_disabled", "User has not enabled live trading.")
        if not user.auto_trading_enabled:
            return self._blocked("user_auto_trading_disabled", "User has not enabled auto trading.")
        if risk_profile is None or not risk_profile.allow_live_trading:
            return self._blocked("risk_profile_live_disabled", "Risk profile does not allow live trading.")
        if not risk_profile.allow_auto_trading:
            return self._blocked("risk_profile_auto_disabled", "Risk profile does not allow auto trading.")
        if not broker_account.static_ip_verified:
            return self._blocked("static_ip_not_verified", "Broker account static IP is not verified.")
        if not payload.strategy_id:
            return self._blocked("strategy_id_required", "Live auto order requires strategy_id.")
        if not payload.strategy_version:
            return self._blocked("strategy_version_required", "Live auto order requires strategy_version.")
        if not payload.algo_tag:
            return self._blocked("algo_tag_required", "Live auto order requires algo_tag.")
        if strategy is None:
            return self._blocked("strategy_required", "Live auto order requires a strategy.")
        if strategy.mode != "live":
            return self._blocked("strategy_not_live", "Strategy must be in LIVE mode.")
        if strategy.status != "RUNNING":
            return self._blocked("strategy_not_running", "Strategy must be RUNNING.")
        if payload.strategy_id != strategy.id:
            return self._blocked("strategy_id_mismatch", "Live auto order strategy_id does not match the strategy.")
        if payload.strategy_version != strategy.version:
            return self._blocked("strategy_version_mismatch", "Live auto order strategy_version does not match the strategy.")

        config = dict(strategy.config or {})
        for key in ("max_daily_loss", "max_trades_per_day", "max_open_positions", "allowed_symbols", "start_time", "stop_time"):
            if not config.get(key):
                return self._blocked("strategy_risk_config_missing", f"Strategy missing {key}.")

        if payload.order_type not in {OrderType.LIMIT, OrderType.SL_LIMIT}:
            return self._blocked("auto_order_type_not_allowed", "Live auto orders must be LIMIT or SL_LIMIT.")

        allowed_symbols = {str(symbol).upper() for symbol in config.get("allowed_symbols", [])}
        if payload.symbol.upper() not in allowed_symbols:
            return self._blocked("symbol_not_allowed", "Symbol is not allowed for this strategy.")

        now_time = datetime.now().time()
        start_time = datetime.fromisoformat(f"2000-01-01T{config['start_time']}").time()
        stop_time = datetime.fromisoformat(f"2000-01-01T{config['stop_time']}").time()
        if not (start_time <= now_time <= stop_time):
            return self._blocked("outside_strategy_window", "Order is outside the strategy allowed time window.")

        if strategy_pnl <= -abs(Decimal(str(config["max_daily_loss"]))):
            return self._blocked("strategy_max_loss_reached", "Strategy max daily loss reached.")
        if len(recent_strategy_orders) >= int(config["max_trades_per_day"]):
            return self._blocked("strategy_max_trades_reached", "Strategy max trades per day reached.")
        if strategy_open_positions >= int(config["max_open_positions"]):
            return self._blocked("strategy_max_open_positions_reached", "Strategy max open positions reached.")
        if any(order.correlation_id == signal_uid for order in recent_strategy_orders):
            return self._blocked("duplicate_signal_id", "Duplicate strategy signal ID rejected.")

        return AutoTradingDecision(True, "auto_trading_guard_approved", "Live auto trading guard approved.")

    def _blocked(self, rule: str, reason: str) -> AutoTradingDecision:
        return AutoTradingDecision(False, rule, reason)


auto_trading_guard = AutoTradingGuard()
