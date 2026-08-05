from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PluginMigration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registro de qué migraciones de cada plugin ya se aplicaron al esquema
    compartido. Tabla del Core (aplicar las migraciones de un plugin es
    responsabilidad del Plugin Manager, sección 4 del CLAUDE.md) — el SQL en
    sí vive en el plugin, en /plugins/<nombre>/migrations. No lleva
    company_id: las tablas de un plugin (plg_<nombre>_...) son de esquema
    compartido, no por tenant — el aislamiento entre tenants pasa por la
    columna company_id de esas tablas, no por el esquema."""

    __tablename__ = "plugin_migrations"
    __table_args__ = (UniqueConstraint("plugin_name", "filename", name="uq_plugin_migration"),)

    plugin_name: Mapped[str] = mapped_column(nullable=False)
    filename: Mapped[str] = mapped_column(nullable=False)
