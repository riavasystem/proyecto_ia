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
        json={"name": "CI test key", "environment": "test", "scopes": scopes},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["key"]  # type: ignore[no-any-return]


async def test_public_endpoint_requires_valid_api_key(client: AsyncClient) -> None:
    response = await client.get("/api/v1/public/services", headers=_auth("sk_test_not-a-real-key"))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_public_endpoint_without_key_is_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/public/services")
    assert response.status_code == 401


async def test_api_key_without_scope_is_forbidden(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Scopes", "scopes@example.com")
    key = await _create_api_key(client, admin_token, scopes=["conversations:read"])

    response = await client.get("/api/v1/public/services", headers=_auth(key))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_public_api_key_sees_only_its_own_tenant_data(client: AsyncClient) -> None:
    admin_a = await _register(client, "Empresa A", "admin-a@example.com")
    admin_b = await _register(client, "Empresa B", "admin-b@example.com")

    await client.post(
        "/api/v1/admin/services",
        json={"name": "Manicure", "price": 8000},
        headers=_auth(admin_a),
    )
    await client.post(
        "/api/v1/admin/services",
        json={"name": "Corte de barba", "price": 5000},
        headers=_auth(admin_b),
    )

    key_a = await _create_api_key(client, admin_a, scopes=["catalog:read"])
    key_b = await _create_api_key(client, admin_b, scopes=["catalog:read"])

    services_a = await client.get("/api/v1/public/services", headers=_auth(key_a))
    assert services_a.status_code == 200
    names_a = [s["name"] for s in services_a.json()["data"]]
    assert names_a == ["Manicure"]

    services_b = await client.get("/api/v1/public/services", headers=_auth(key_b))
    assert services_b.status_code == 200
    names_b = [s["name"] for s in services_b.json()["data"]]
    assert names_b == ["Corte de barba"]


async def test_revoked_api_key_is_rejected(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Revoke", "revoke@example.com")

    create_response = await client.post(
        "/api/v1/admin/api-keys",
        json={"name": "to revoke", "environment": "test", "scopes": ["catalog:read"]},
        headers=_auth(admin_token),
    )
    key_id = create_response.json()["id"]
    key = create_response.json()["key"]

    revoke_response = await client.delete(
        f"/api/v1/admin/api-keys/{key_id}", headers=_auth(admin_token)
    )
    assert revoke_response.status_code == 204

    response = await client.get("/api/v1/public/services", headers=_auth(key))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_public_company_endpoint(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Pública", "pub@example.com")
    key = await _create_api_key(client, admin_token, scopes=["catalog:read"])

    response = await client.get("/api/v1/public/company", headers=_auth(key))
    assert response.status_code == 200
    assert response.json()["name"] == "Empresa Pública"
