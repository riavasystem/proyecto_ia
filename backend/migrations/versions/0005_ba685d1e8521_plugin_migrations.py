"""plugin_migrations: registro de migraciones de plugin aplicadas

Revision ID: ba685d1e8521
Revises: 97504d58d228
Create Date: 2026-08-05 00:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ba685d1e8521"
down_revision: str | None = "97504d58d228"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plugin_migrations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("plugin_name", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_unique_constraint(
        "uq_plugin_migration", "plugin_migrations", ["plugin_name", "filename"]
    )


def downgrade() -> None:
    op.drop_table("plugin_migrations")
