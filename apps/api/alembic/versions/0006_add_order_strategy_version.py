"""add order strategy version

Revision ID: 0006_add_order_strategy_version
Revises: 0005_add_alerts
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_add_order_strategy_version"
down_revision: str | None = "0005_add_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("strategy_version", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "strategy_version")
