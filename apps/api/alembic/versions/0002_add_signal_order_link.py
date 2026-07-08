"""add signal order link

Revision ID: 0002_add_signal_order_link
Revises: 0001_create_foundation_schema
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_signal_order_link"
down_revision: str | None = "0001_create_foundation_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(sa.Column("order_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_signals_order_id_orders",
            "orders",
            ["order_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_constraint("fk_signals_order_id_orders", type_="foreignkey")
        batch_op.drop_column("order_id")
