import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.plugins_runtime.interface import PluginContext, PluginManifest, PluginResult

_DATETIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")
_TRIGGER_WORDS = {"reservar", "agendar", "agenda", "cita", "turno", "para", "el", "de"}

# El plugin nunca importa módulos internos del Core fuera de app.plugins_runtime
# (sección 8 del CLAUDE.md). sqlalchemy es una dependencia externa normal, no
# un módulo interno de la plataforma.

manifest = PluginManifest(
    name="agenda",
    version="1.0.0",
    author="",
    description="Agenda y reservas de citas para el negocio.",
    category="productividad",
    dependencies=[],
    permissions=["conversations.read", "agenda.write"],
    hooks=["message.received", "conversation.closed"],
    screens=[{"path": "/agenda", "label": "Agenda", "icon": "calendar"}],
    chat_triggers=["reservar", "agendar", "agenda", "cita", "turno"],
)

_TABLE = "plg_agenda_bookings"

_CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    id VARCHAR PRIMARY KEY,
    company_id VARCHAR NOT NULL,
    service_name VARCHAR NOT NULL,
    scheduled_at VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    notes VARCHAR,
    created_at VARCHAR NOT NULL
)
"""


class AgendaPlugin:
    manifest = manifest

    async def install(self, ctx: PluginContext) -> None:
        await ctx.db.execute(text(_CREATE_TABLE_SQL))
        await ctx.db.commit()

    async def update(self, ctx: PluginContext) -> None:
        pass

    async def uninstall(self, ctx: PluginContext) -> None:
        # No se borra la tabla ni las reservas: son datos del tenant, no del
        # runtime del plugin. Si el tenant reinstala, las recupera.
        pass

    async def configure(self, ctx: PluginContext, config: dict[str, Any]) -> None:
        pass

    async def check_permissions(self, ctx: PluginContext, action: str) -> bool:
        return action in {"create_booking", "list_bookings", "chat"}

    async def execute(
        self, ctx: PluginContext, action: str, payload: dict[str, Any]
    ) -> PluginResult:
        if action == "create_booking":
            return await self._create_booking(ctx, payload)
        if action == "list_bookings":
            return await self._list_bookings(ctx)
        if action == "chat":
            return await self._handle_chat(ctx, payload)
        return PluginResult(success=False, message=f"Acción desconocida: {action}")

    async def _handle_chat(self, ctx: PluginContext, payload: dict[str, Any]) -> PluginResult:
        """Entrada desde el motor de IA (app/ai/engine.py) cuando el mensaje
        matchea uno de los chat_triggers del manifiesto. Parseo deliberadamente
        simple: sin LLM, solo reconoce 'AAAA-MM-DD HH:MM' en el texto."""
        message = str(payload.get("message", ""))
        match = _DATETIME_PATTERN.search(message)
        if match is None:
            return PluginResult(
                success=True,
                message=(
                    "Puedo ayudarte a agendar un turno. Decime el servicio y la fecha/hora "
                    "en formato AAAA-MM-DD HH:MM, por ejemplo: 'reservar Corte 2026-09-01 15:00'."
                ),
            )

        scheduled_at = match.group(0).replace(" ", "T")
        remainder = (message[: match.start()] + message[match.end() :]).strip()
        service_words = [w for w in remainder.split() if w.lower() not in _TRIGGER_WORDS]
        service_name = " ".join(service_words).strip() or "Reserva"

        result = await self._create_booking(
            ctx, {"service_name": service_name, "scheduled_at": scheduled_at}
        )
        if not result.success:
            return result
        return PluginResult(
            success=True,
            message=f"Listo, agendé '{service_name}' para el {scheduled_at.replace('T', ' ')}.",
            data=result.data,
        )

    async def _create_booking(self, ctx: PluginContext, payload: dict[str, Any]) -> PluginResult:
        service_name = payload.get("service_name")
        scheduled_at = payload.get("scheduled_at")
        if not service_name or not scheduled_at:
            return PluginResult(success=False, message="Faltan 'service_name' o 'scheduled_at'")

        try:
            datetime.fromisoformat(scheduled_at)
        except (TypeError, ValueError):
            return PluginResult(success=False, message="'scheduled_at' debe ser ISO 8601")

        booking_id = str(uuid.uuid4())
        await ctx.db.execute(
            text(
                f"INSERT INTO {_TABLE} "
                "(id, company_id, service_name, scheduled_at, notes, created_at) "
                "VALUES (:id, :company_id, :service_name, :scheduled_at, :notes, :created_at)"
            ),
            {
                "id": booking_id,
                "company_id": str(ctx.company_id),
                "service_name": service_name,
                "scheduled_at": scheduled_at,
                "notes": payload.get("notes"),
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        await ctx.db.commit()
        return PluginResult(
            success=True,
            message="Reserva creada",
            data={
                "booking_id": booking_id,
                "service_name": service_name,
                "scheduled_at": scheduled_at,
            },
        )

    async def _list_bookings(self, ctx: PluginContext) -> PluginResult:
        result = await ctx.db.execute(
            text(
                f"SELECT id, service_name, scheduled_at, status FROM {_TABLE} "
                "WHERE company_id = :company_id ORDER BY scheduled_at"
            ),
            {"company_id": str(ctx.company_id)},
        )
        bookings = [
            {
                "id": row.id,
                "service_name": row.service_name,
                "scheduled_at": row.scheduled_at,
                "status": row.status,
            }
            for row in result
        ]
        return PluginResult(success=True, message="", data={"bookings": bookings})


plugin = AgendaPlugin()
