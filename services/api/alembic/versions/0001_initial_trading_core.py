"""initial trading core

Revision ID: 0001_initial_trading_core
Revises:
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_trading_core"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("broker_account_id", sa.String(length=80), nullable=False),
        sa.Column("client_order_key", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("symbol", sa.String(length=80), nullable=False),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("order_type", sa.String(length=20), nullable=False),
        sa.Column("product", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=True),
        sa.Column("estimated_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("broker_order_id", sa.String(length=120), nullable=True),
        sa.Column("strategy_id", sa.String(length=80), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
    )
    op.create_index("ix_orders_correlation_id", "orders", ["correlation_id"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_broker_account_id", "orders", ["broker_account_id"])
    op.create_index(
        "ix_orders_user_account_created", "orders", ["user_id", "broker_account_id", "created_at"]
    )

    op.create_table(
        "risk_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("broker_account_id", sa.String(length=80), nullable=False),
        sa.Column("is_configured", sa.Boolean(), nullable=False),
        sa.Column("allow_live_trading", sa.Boolean(), nullable=False),
        sa.Column("max_order_quantity", sa.Integer(), nullable=False),
        sa.Column("max_order_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("max_day_notional", sa.Numeric(18, 2), nullable=False),
        sa.Column("allowed_products", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "broker_account_id", name="uq_risk_profile_user_account"),
    )

    op.create_table(
        "broker_credentials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=False),
        sa.Column("broker_account_id", sa.String(length=80), nullable=False),
        sa.Column("broker_name", sa.String(length=80), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("encrypted_api_secret", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "broker_account_id", "broker_name", name="uq_broker_credentials_account_name"
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=True),
        sa.Column("broker_account_id", sa.String(length=80), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("request", sa.JSON(), nullable=True),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_index(
        "ix_audit_events_correlation", "audit_events", ["correlation_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("broker_credentials")
    op.drop_table("risk_profiles")
    op.drop_table("orders")

