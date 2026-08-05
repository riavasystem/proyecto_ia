"""company_id FK con ON DELETE CASCADE hacia companies

Hasta ahora company_id era una columna UUID simple, sin referencia real a
companies.id: borrar una empresa dejaba filas huérfanas en todas las
tablas del Core (encontrado en la limpieza de datos de prueba de la Fase
11b/11c). Esto agrega la FK con cascada para que borrar una empresa borre
también todos sus datos, en vez de dejarlos sueltos.

No incluye tablas de plugins (p. ej. plg_agenda_bookings): esas manejan su
propio esquema por fuera de esta cadena de Alembic (ver plugins_runtime),
y en el caso de "agenda" su company_id es VARCHAR, no UUID, así que
necesitaría su propia migración de plugin con un cast de tipo.

Revision ID: a1f3c9e2b4d7
Revises: 6745d54e8299
Create Date: 2026-08-05 00:00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1f3c9e2b4d7"
down_revision: str | None = "6745d54e8299"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

TABLES = (
    "contacts",
    "conversations",
    "messages",
    "services",
    "users",
    "products",
    "branches",
    "business_hours",
    "schedule_exceptions",
    "promotions",
    "policies",
    "faqs",
    "installed_plugins",
    "webhook_endpoints",
    "webhook_deliveries",
    "api_keys",
)


def _constraint_name(table: str) -> str:
    return f"fk_{table}_company_id_companies"


def upgrade() -> None:
    for table in TABLES:
        op.create_foreign_key(
            _constraint_name(table),
            table,
            "companies",
            ["company_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(_constraint_name(table), table, type_="foreignkey")
