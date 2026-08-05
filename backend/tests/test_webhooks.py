import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import select

import app.services.webhooks as webhooks_service
from app.db import session as db_session
from app.models.webhook import WebhookDelivery


async def _wait_for_deliveries(expected_count: int, timeout: float = 5.0) -> list[WebhookDelivery]:
    """El worker de la cola procesa las entregas de forma asíncrona (vía
    Redis + BLPOP), así que hay que esperar activamente en vez de asumir que
    ya terminó cuando el endpoint /chat responde."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async with db_session.async_session_factory() as session:
            result = await session.execute(select(WebhookDelivery))
            deliveries = list(result.scalars().all())
        if len(deliveries) >= expected_count and all(d.status != "pending" for d in deliveries):
            return deliveries
        await asyncio.sleep(0.05)
    raise AssertionError(f"timeout esperando {expected_count} entregas de webhook")


async def _register(client: AsyncClient, company_name: str, email: str) -> str:
    response = await client.post(
        "/api/v1/admin/auth/register",
        json={"company_name": company_name, "admin_email": email, "admin_password": "s3cret-pass"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]  # type: ignore[no-any-return]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_sign_payload_is_deterministic_and_covers_timestamp() -> None:
    body = b'{"hello":"world"}'
    sig_a = webhooks_service.sign_payload("secret", "1000", body)
    sig_b = webhooks_service.sign_payload("secret", "1000", body)
    sig_c = webhooks_service.sign_payload("secret", "2000", body)
    assert sig_a == sig_b
    assert sig_a != sig_c


async def test_create_webhook_rejects_unknown_event(client: AsyncClient) -> None:
    admin_token = await _register(
        client, "Empresa Webhooks Inválidos", "webhooks-invalid@example.com"
    )
    response = await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["not.a.real.event"]},
        headers=_auth(admin_token),
    )
    assert response.status_code == 422


async def test_create_list_and_delete_webhook(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Webhooks CRUD", "webhooks-crud@example.com")

    create = await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["message.received"]},
        headers=_auth(admin_token),
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["secret"]
    webhook_id = body["id"]

    listing = await client.get("/api/v1/admin/webhooks", headers=_auth(admin_token))
    assert len(listing.json()) == 1
    assert "secret" not in listing.json()[0]

    delete = await client.delete(f"/api/v1/admin/webhooks/{webhook_id}", headers=_auth(admin_token))
    assert delete.status_code == 204

    listing_after = await client.get("/api/v1/admin/webhooks", headers=_auth(admin_token))
    assert listing_after.json() == []


async def test_chat_emits_webhook_and_delivers_successfully(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin_token = await _register(
        client, "Empresa Webhooks Delivery", "webhooks-delivery@example.com"
    )
    await client.post(
        "/api/v1/admin/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["message.received", "conversation.started"],
        },
        headers=_auth(admin_token),
    )
    key_response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "webhooks test key", "environment": "test", "scopes": ["chat:write"]},
        headers=_auth(admin_token),
    )
    key = key_response.json()["key"]

    calls: list[str] = []

    async def fake_send(url: str, body: bytes, headers: dict[str, str]) -> int:
        calls.append(url)
        return 200

    monkeypatch.setattr(webhooks_service, "_send", fake_send)

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key),
    )
    assert response.status_code == 200

    deliveries = await _wait_for_deliveries(expected_count=2)

    event_types = {d.event_type for d in deliveries}
    assert event_types == {"message.received", "conversation.started"}
    assert all(d.status == "success" for d in deliveries)
    assert len(calls) == 2


async def test_webhook_with_no_matching_event_is_not_notified(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin_token = await _register(
        client, "Empresa Webhooks Sin Match", "webhooks-nomatch@example.com"
    )
    await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["conversation.closed"]},
        headers=_auth(admin_token),
    )
    key_response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "webhooks nomatch key", "environment": "test", "scopes": ["chat:write"]},
        headers=_auth(admin_token),
    )
    key = key_response.json()["key"]

    async def fake_send(url: str, body: bytes, headers: dict[str, str]) -> int:
        raise AssertionError("no debería llamarse: el evento no matchea ningún webhook suscripto")

    monkeypatch.setattr(webhooks_service, "_send", fake_send)

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key),
    )
    assert response.status_code == 200
    await asyncio.sleep(0)


async def test_webhook_isolated_per_tenant(client: AsyncClient) -> None:
    admin_a = await _register(client, "Empresa Webhooks A", "webhooks-a@example.com")
    admin_b = await _register(client, "Empresa Webhooks B", "webhooks-b@example.com")

    await client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook-a", "events": ["message.received"]},
        headers=_auth(admin_a),
    )

    listing_b = await client.get("/api/v1/admin/webhooks", headers=_auth(admin_b))
    assert listing_b.json() == []
