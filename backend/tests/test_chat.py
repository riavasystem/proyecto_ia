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
        json={"name": "chat test key", "environment": "test", "scopes": scopes},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["key"]  # type: ignore[no-any-return]


async def test_chat_greeting(client: AsyncClient) -> None:
    admin_token = await _register(client, "Peluquería Test", "greet@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "Hola, buenas tardes"},
        headers=_auth(key),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "Peluquería Test" in body["reply"]
    assert body["conversation_id"]


async def test_chat_services_intent_uses_real_catalog(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Servicios", "services-chat@example.com")
    await client.post(
        "/api/v1/admin/services",
        json={"name": "Corte de pelo", "price": 12000},
        headers=_auth(admin_token),
    )
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "¿Cuánto cuesta el servicio?"},
        headers=_auth(key),
    )
    assert response.status_code == 200
    assert "Corte de pelo" in response.json()["reply"]


async def test_chat_faq_match_takes_priority(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa FAQ", "faq-chat@example.com")
    await client.post(
        "/api/v1/admin/faqs",
        json={
            "question": "¿Aceptan tarjeta de crédito?",
            "answer": "Sí, aceptamos todas las tarjetas.",
        },
        headers=_auth(admin_token),
    )
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "aceptan tarjeta de credito?"},
        headers=_auth(key),
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Sí, aceptamos todas las tarjetas."


async def test_chat_conversation_continues_with_same_id(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Continuidad", "continuidad@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write", "conversations:read"])

    first = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key),
    )
    conversation_id = first.json()["conversation_id"]

    second = await client.post(
        "/api/v1/public/chat",
        json={
            "external_user_id": "user-1",
            "conversation_id": conversation_id,
            "message": "¿tienen promociones?",
        },
        headers=_auth(key),
    )
    assert second.json()["conversation_id"] == conversation_id

    detail = await client.get(f"/api/v1/public/conversations/{conversation_id}", headers=_auth(key))
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 4  # 2 del usuario + 2 del asistente


async def test_chat_tenant_isolation_on_conversations(client: AsyncClient) -> None:
    admin_a = await _register(client, "Empresa Chat A", "chat-a@example.com")
    admin_b = await _register(client, "Empresa Chat B", "chat-b@example.com")
    key_a = await _create_api_key(client, admin_a, scopes=["chat:write", "conversations:read"])
    key_b = await _create_api_key(client, admin_b, scopes=["chat:write", "conversations:read"])

    chat_response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key_a),
    )
    conversation_id = chat_response.json()["conversation_id"]

    response = await client.get(
        f"/api/v1/public/conversations/{conversation_id}", headers=_auth(key_b)
    )
    assert response.status_code == 404


async def test_close_conversation(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Cierre", "cierre@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    chat_response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key),
    )
    conversation_id = chat_response.json()["conversation_id"]

    close_response = await client.post(
        f"/api/v1/public/conversations/{conversation_id}/close", headers=_auth(key)
    )
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"


async def test_chat_delegates_to_installed_plugin_with_matching_trigger(
    client: AsyncClient,
) -> None:
    admin_token = await _register(client, "Peluquería Agenda Chat", "agenda-chat@example.com")
    install = await client.post(
        "/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token)
    )
    assert install.status_code == 201, install.text
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.post(
        "/api/v1/public/chat",
        json={
            "external_user_id": "user-1",
            "message": "quiero reservar un Corte 2026-09-01 15:00",
        },
        headers=_auth(key),
    )
    assert response.status_code == 200, response.text
    assert "agendé" in response.json()["reply"].lower()

    bookings = await client.post(
        "/api/v1/public/plugins/agenda/execute",
        json={"action": "list_bookings", "payload": {}},
        headers=_auth(await _create_api_key(client, admin_token, scopes=["plugins:execute"])),
    )
    assert len(bookings.json()["data"]["bookings"]) == 1


async def test_chat_falls_back_when_no_plugin_trigger_matches(client: AsyncClient) -> None:
    admin_token = await _register(client, "Peluquería Sin Match", "sin-match@example.com")
    await client.post("/api/v1/admin/plugins/agenda/install", headers=_auth(admin_token))
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola, buenas"},
        headers=_auth(key),
    )
    assert response.status_code == 200
    assert "Peluquería Sin Match" in response.json()["reply"]


async def test_chat_ignores_uninstalled_plugin_triggers(client: AsyncClient) -> None:
    admin_token = await _register(client, "Peluquería Sin Plugin", "sin-plugin@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "quiero reservar hora"},
        headers=_auth(key),
    )
    assert response.status_code == 200
    # Sin el plugin instalado, cae al flujo genérico (no inventa una reserva)
    assert "agendé" not in response.json()["reply"].lower()


async def test_admin_can_list_and_view_conversations(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Panel", "panel@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write"])

    chat_response = await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key),
    )
    conversation_id = chat_response.json()["conversation_id"]

    list_response = await client.get("/api/v1/admin/conversations", headers=_auth(admin_token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = await client.get(
        f"/api/v1/admin/conversations/{conversation_id}", headers=_auth(admin_token)
    )
    assert detail_response.status_code == 200
    assert len(detail_response.json()["messages"]) == 2
