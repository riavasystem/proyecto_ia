from httpx import AsyncClient
from sqlalchemy import select

from app.db import session as db_session
from app.models.plugin_migration import PluginMigration


async def _register(client: AsyncClient, company_name: str, email: str) -> str:
    response = await client.post(
        "/api/v1/admin/auth/register",
        json={"company_name": company_name, "admin_email": email, "admin_password": "s3cret-pass"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]  # type: ignore[no-any-return]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_install_applies_migration_and_records_it(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Migraciones", "migraciones@example.com")

    install = await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token))
    assert install.status_code == 201, install.text

    async with db_session.async_session_factory() as session:
        result = await session.execute(
            select(PluginMigration).where(PluginMigration.plugin_name == "agenda")
        )
        applied = result.scalars().all()

    assert [m.filename for m in applied] == ["0001_create_bookings_table.sql"]


async def test_migration_is_not_reapplied_for_a_second_tenant(client: AsyncClient) -> None:
    admin_a = await _register(client, "Empresa Migraciones A", "migraciones-a@example.com")
    admin_b = await _register(client, "Empresa Migraciones B", "migraciones-b@example.com")

    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_a))
    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_b))

    async with db_session.async_session_factory() as session:
        result = await session.execute(
            select(PluginMigration).where(PluginMigration.plugin_name == "agenda")
        )
        applied = result.scalars().all()

    # Es una migración de esquema compartido, no una por tenant: se aplica una sola vez.
    assert len(applied) == 1


async def test_agenda_bookings_table_works_end_to_end_after_migration(
    client: AsyncClient,
) -> None:
    admin_token = await _register(client, "Empresa Migraciones E2E", "migraciones-e2e@example.com")
    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token))

    key_response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "migrations e2e", "environment": "test", "scopes": ["plugins:execute"]},
        headers=_auth(admin_token),
    )
    key = key_response.json()["key"]

    create_response = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={
            "action": "create_booking",
            "payload": {"service_name": "Corte", "scheduled_at": "2026-09-01T15:00:00"},
        },
        headers={"Authorization": f"Bearer {key}"},
    )
    assert create_response.json()["success"] is True
