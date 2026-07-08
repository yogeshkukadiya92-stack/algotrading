"""add order hardening indexes

Revision ID: 0007_add_order_hardening_indexes
Revises: 0006_add_order_strategy_version
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_add_order_hardening_indexes"
down_revision: str | None = "0006_add_order_strategy_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.add_column("orders", sa.Column("request_fingerprint", sa.String(length=64), nullable=False, server_default=""))
    op.create_index("uq_orders_user_idempotency_key", "orders", ["user_id", "idempotency_key"], unique=True)
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)
    op.create_index("ix_orders_correlation_id", "orders", ["correlation_id"], unique=False)
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"], unique=False)
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"], unique=False)
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], unique=False)
    op.create_index("ix_signals_strategy_id", "signals", ["strategy_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_signals_strategy_id", table_name="signals")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_order_events_order_id", table_name="order_events")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_correlation_id", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_index("uq_orders_user_idempotency_key", table_name="orders")
    op.drop_column("orders", "request_fingerprint")
    op.drop_column("orders", "idempotency_key")
