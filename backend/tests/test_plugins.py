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
        json={"name": "plugin test key", "environment": "test", "scopes": scopes},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["key"]  # type: ignore[no-any-return]


async def test_agenda_plugin_is_discovered_but_not_installed_by_default(
    client: AsyncClient,
) -> None:
    admin_token = await _register(client, "Empresa Plugins", "plugins@example.com")

    response = await client.get("/api/v1/admin/plugins", headers=_auth(admin_token))
    assert response.status_code == 200
    plugins = {p["manifest"]["name"]: p for p in response.json()}
    assert "agenda" in plugins
    assert plugins["agenda"]["installation"] is None


async def test_execute_before_install_is_gracefully_rejected(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Sin Instalar", "sininstalar@example.com")
    key = await _create_api_key(client, admin_token, scopes=["plugins:execute"])

    response = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={"action": "create_booking", "payload": {}},
        headers=_auth(key),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert "no instalado" in body["message"].lower()


async def test_install_configure_and_book_via_agenda_plugin(client: AsyncClient) -> None:
    admin_token = await _register(client, "Peluquería Agenda", "agenda@example.com")

    install = await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token))
    assert install.status_code == 201, install.text
    assert install.json()["plugin_name"] == "agenda"
    assert install.json()["is_enabled"] is True

    key = await _create_api_key(client, admin_token, scopes=["plugins:execute"])

    create_response = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={
            "action": "create_booking",
            "payload": {"service_name": "Corte", "scheduled_at": "2026-09-01T15:00:00"},
        },
        headers=_auth(key),
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    assert create_body["success"] is True
    assert create_body["data"]["service_name"] == "Corte"

    list_response = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={"action": "list_bookings", "payload": {}},
        headers=_auth(key),
    )
    bookings = list_response.json()["data"]["bookings"]
    assert len(bookings) == 1
    assert bookings[0]["service_name"] == "Corte"


async def test_agenda_plugin_bookings_are_isolated_per_tenant(client: AsyncClient) -> None:
    admin_a = await _register(client, "Empresa Agenda A", "agenda-a@example.com")
    admin_b = await _register(client, "Empresa Agenda B", "agenda-b@example.com")

    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_a))
    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_b))

    key_a = await _create_api_key(client, admin_a, scopes=["plugins:execute"])
    key_b = await _create_api_key(client, admin_b, scopes=["plugins:execute"])

    await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={
            "action": "create_booking",
            "payload": {"service_name": "Manicure", "scheduled_at": "2026-09-01T10:00:00"},
        },
        headers=_auth(key_a),
    )

    list_b = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={"action": "list_bookings", "payload": {}},
        headers=_auth(key_b),
    )
    assert list_b.json()["data"]["bookings"] == []


async def test_unknown_action_is_rejected_by_check_permissions(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Acción Rara", "accion-rara@example.com")
    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token))
    key = await _create_api_key(client, admin_token, scopes=["plugins:execute"])

    response = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={"action": "delete_everything", "payload": {}},
        headers=_auth(key),
    )
    body = response.json()
    assert body["success"] is False
    assert "no permitida" in body["message"].lower()


async def test_uninstall_then_execute_is_rejected_again(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Desinstala", "desinstala@example.com")
    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token))

    uninstall = await client.delete(
        "/api/v1/admin/plugins/agenda/uninstall", headers=_auth(admin_token)
    )
    assert uninstall.status_code == 204

    key = await _create_api_key(client, admin_token, scopes=["plugins:execute"])
    response = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={"action": "list_bookings", "payload": {}},
        headers=_auth(key),
    )
    assert response.json()["success"] is False
