"""installed_plugins: estado de instalación de plugins por tenant

Revision ID: 97504d58d228
Revises: c7237ba98591
Create Date: 2026-08-04 00:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "97504d58d228"
down_revision: str | None = "c7237ba98591"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "installed_plugins",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("plugin_name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_installed_plugins_company_id", "installed_plugins", ["company_id"])
    op.create_unique_constraint(
        "uq_installed_plugins_company_plugin", "installed_plugins", ["company_id", "plugin_name"]
    )


def downgrade() -> None:
    op.drop_table("installed_plugins")
