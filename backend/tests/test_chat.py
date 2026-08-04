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
