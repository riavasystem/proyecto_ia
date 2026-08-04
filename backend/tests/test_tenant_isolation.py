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


async def test_register_and_login(client: AsyncClient) -> None:
    token = await _register(client, "Empresa A", "admin-a@example.com")
    assert token

    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "admin-a@example.com", "password": "s3cret-pass"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_with_wrong_password_fails(client: AsyncClient) -> None:
    await _register(client, "Empresa Login", "admin-login@example.com")

    response = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "admin-login@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_service_crud_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/services")
    assert response.status_code == 401


async def test_tenant_cannot_see_other_tenant_services(client: AsyncClient) -> None:
    token_a = await _register(client, "Empresa A", "a@example.com")
    token_b = await _register(client, "Empresa B", "b@example.com")

    create_response = await client.post(
        "/api/v1/admin/services",
        json={"name": "Corte de pelo", "price": 12000},
        headers=_auth(token_a),
    )
    assert create_response.status_code == 201
    service_id = create_response.json()["id"]

    # La empresa A ve su propio servicio.
    list_a = await client.get("/api/v1/admin/services", headers=_auth(token_a))
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1

    # La empresa B no ve ningún servicio ajeno.
    list_b = await client.get("/api/v1/admin/services", headers=_auth(token_b))
    assert list_b.status_code == 200
    assert list_b.json() == []

    # La empresa B no puede leer el servicio de A por id directo (404, no 403,
    # para no filtrar la existencia del recurso).
    get_b = await client.get(f"/api/v1/admin/services/{service_id}", headers=_auth(token_b))
    assert get_b.status_code == 404

    # Tampoco puede editarlo ni borrarlo.
    update_b = await client.patch(
        f"/api/v1/admin/services/{service_id}", json={"name": "hackeado"}, headers=_auth(token_b)
    )
    assert update_b.status_code == 404

    delete_b = await client.delete(f"/api/v1/admin/services/{service_id}", headers=_auth(token_b))
    assert delete_b.status_code == 404

    # El servicio original de A sigue intacto.
    get_a = await client.get(f"/api/v1/admin/services/{service_id}", headers=_auth(token_a))
    assert get_a.status_code == 200
    assert get_a.json()["name"] == "Corte de pelo"
