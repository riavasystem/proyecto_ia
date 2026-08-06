from httpx import AsyncClient


async def _register(client: AsyncClient, company_name: str, email: str) -> str:
    response = await client.post(
        "/api/v1/admin/auth/register",
        json={"company_name": company_name, "admin_email": email, "admin_password": "s3cret-pass"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]  # type: ignore[no-any-return]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_api_key(client: AsyncClient, admin_token: str, scopes: list[str]) -> str:
    response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "webhooks public test key", "environment": "test", "scopes": scopes},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["key"]  # type: ignore[no-any-return]


async def test_public_webhooks_requires_scope(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Webhooks Public Sin Scope", "wpub-1@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.get("/api/v1/public/webhooks", headers=_auth(key))
    assert response.status_code == 403


async def test_public_webhooks_full_crud_with_scope(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Webhooks Public CRUD", "wpub-2@example.com")
    key = await _create_api_key(client, admin_token, scopes=["webhooks:manage"])
    headers = _auth(key)

    create = await client.post(
        "/api/v1/public/webhooks",
        json={"url": "https://example.com/hook", "events": ["message.received"]},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["secret"]
    webhook_id = body["id"]

    listing = await client.get("/api/v1/public/webhooks", headers=headers)
    assert len(listing.json()) == 1
    assert "secret" not in listing.json()[0]

    update = await client.patch(
        f"/api/v1/public/webhooks/{webhook_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["is_active"] is False

    deliveries = await client.get(
        f"/api/v1/public/webhooks/{webhook_id}/deliveries", headers=headers
    )
    assert deliveries.status_code == 200
    assert deliveries.json() == []

    delete = await client.delete(f"/api/v1/public/webhooks/{webhook_id}", headers=headers)
    assert delete.status_code == 204

    listing_after = await client.get("/api/v1/public/webhooks", headers=headers)
    assert listing_after.json() == []


async def test_public_webhooks_isolated_per_tenant(client: AsyncClient) -> None:
    admin_a = await _register(client, "Empresa Webhooks Public A", "wpub-a@example.com")
    admin_b = await _register(client, "Empresa Webhooks Public B", "wpub-b@example.com")
    key_a = await _create_api_key(client, admin_a, scopes=["webhooks:manage"])
    key_b = await _create_api_key(client, admin_b, scopes=["webhooks:manage"])

    create = await client.post(
        "/api/v1/public/webhooks",
        json={"url": "https://example.com/hook-a", "events": ["message.received"]},
        headers=_auth(key_a),
    )
    webhook_id = create.json()["id"]

    listing_b = await client.get("/api/v1/public/webhooks", headers=_auth(key_b))
    assert listing_b.json() == []

    get_other_tenant = await client.get(
        f"/api/v1/public/webhooks/{webhook_id}/deliveries", headers=_auth(key_b)
    )
    assert get_other_tenant.status_code == 404
