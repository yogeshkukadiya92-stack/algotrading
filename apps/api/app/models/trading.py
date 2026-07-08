from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid4())


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    live_trading_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    auto_trading_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    broker_accounts: Mapped[list[BrokerAccount]] = relationship(back_populates="user")
    risk_profiles: Mapped[list[RiskProfile]] = relationship(back_populates="user")
    orders: Mapped[list[Order]] = relationship(back_populates="user")
    trades: Mapped[list[Trade]] = relationship(back_populates="user")
    positions: Mapped[list[Position]] = relationship(back_populates="user")
    signals: Mapped[list[Signal]] = relationship(back_populates="user")
    strategies: Mapped[list[Strategy]] = relationship(back_populates="user")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="user")
    alerts: Mapped[list[Alert]] = relationship(back_populates="user")
    pnl_snapshots: Mapped[list[PnlSnapshot]] = relationship(back_populates="user")
    backtest_runs: Mapped[list[BacktestRun]] = relationship(back_populates="user")
    system_controls: Mapped[list[SystemControl]] = relationship(back_populates="user")


class BrokerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "broker_accounts"
    __table_args__ = (
        Index("ix_broker_accounts_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_paper: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    static_ip_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="broker_accounts")
    orders: Mapped[list[Order]] = relationship(back_populates="broker_account")
    positions: Mapped[list[Position]] = relationship(back_populates="broker_account")


class Instrument(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("broker_name", "instrument_token", name="uq_instruments_broker_token"),
        Index("ix_instruments_lookup", "exchange", "segment", "symbol"),
    )

    broker_name: Mapped[str] = mapped_column(String(80), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    segment: Mapped[str] = mapped_column(String(30), nullable=False)
    symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    trading_symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    instrument_token: Mapped[int] = mapped_column(BigInteger, nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    tick_size: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0.05"))
    expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class RiskProfile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "risk_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_risk_profiles_user_id"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    max_daily_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_order_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_lots_per_order: Mapped[int] = mapped_column(Integer, nullable=False)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    allowed_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    auto_square_off_time: Mapped[time] = mapped_column(Time, nullable=False)
    allow_live_trading: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    allow_auto_trading: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    user: Mapped[User] = relationship(back_populates="risk_profiles")


class Strategy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "strategies"
    __table_args__ = (Index("ix_strategies_user_status", "user_id", "status"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship(back_populates="strategies")
    signals: Mapped[list[Signal]] = relationship(back_populates="strategy")
    orders: Mapped[list[Order]] = relationship(back_populates="strategy")


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("correlation_id", name="uq_orders_correlation_id"),
        Index("uq_orders_user_idempotency_key", "user_id", "idempotency_key", unique=True),
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_correlation_id", "correlation_id"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_user_created", "user_id", "created_at"),
        Index("ix_orders_broker_account_created", "broker_account_id", "created_at"),
    )

    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_account_id: Mapped[str] = mapped_column(ForeignKey("broker_accounts.id"), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(80), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    strategy_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    segment: Mapped[str] = mapped_column(String(30), nullable=False)
    instrument_token: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(12), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    trigger_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    risk_status: Mapped[str] = mapped_column(String(40), nullable=False)
    algo_tag: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)

    user: Mapped[User] = relationship(back_populates="orders")
    broker_account: Mapped[BrokerAccount] = relationship(back_populates="orders")
    strategy: Mapped[Strategy | None] = relationship(back_populates="orders")
    events: Mapped[list[OrderEvent]] = relationship(back_populates="order")
    trades: Mapped[list[Trade]] = relationship(back_populates="order")


class OrderEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "order_events"
    __table_args__ = (
        Index("ix_order_events_order_id", "order_id"),
        Index("ix_order_events_order_created", "order_id", "created_at"),
    )

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped[Order] = relationship(back_populates="events")


class Trade(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "trades"
    __table_args__ = (Index("ix_trades_user_traded_at", "user_id", "traded_at"),)

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    brokerage_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    order: Mapped[Order] = relationship(back_populates="trades")
    user: Mapped[User] = relationship(back_populates="trades")


class Position(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("user_id", "broker_account_id", "symbol", name="uq_positions_user_account_symbol"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_account_id: Mapped[str] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ltp: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="positions")
    broker_account: Mapped[BrokerAccount] = relationship(back_populates="positions")


class Signal(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_strategy_id", "strategy_id"),
        Index("ix_signals_user_strategy_created", "user_id", "strategy_id", "created_at"),
    )

    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    side: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    target: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy: Mapped[Strategy] = relationship(back_populates="signals")
    order: Mapped[Order | None] = relationship()
    user: Mapped[User] = relationship(back_populates="signals")


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_user_id", "user_id"),
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_entity", "entity_type", "entity_id", "created_at"),
    )

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User | None] = relationship(back_populates="audit_events")


class Alert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_created", "user_id", "created_at"),
        Index("ix_alerts_user_read", "user_id", "is_read"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="alerts")


class PnlSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "pnl_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_pnl_snapshots_user_date"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="pnl_snapshots")


class BacktestRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (Index("ix_backtest_runs_user_created", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    symbol: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    losing_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="backtest_runs")


class SystemControl(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_controls"
    __table_args__ = (Index("ix_system_controls_user_created", "user_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kill_switch_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="system_controls")
