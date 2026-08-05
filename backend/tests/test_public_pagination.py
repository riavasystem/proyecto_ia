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
        json={"name": "pagination test key", "environment": "test", "scopes": scopes},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["key"]  # type: ignore[no-any-return]


async def test_public_list_paginates_with_cursor(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Paginación", "pagination@example.com")
    for i in range(5):
        response = await client.post(
            "/api/v1/admin/services",
            json={"name": f"Servicio {i}"},
            headers=_auth(admin_token),
        )
        assert response.status_code == 201, response.text
    key = await _create_api_key(client, admin_token, scopes=["catalog:read"])

    first_page = await client.get(
        "/api/v1/public/services", params={"limit": 2}, headers=_auth(key)
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["data"]) == 2
    assert first_body["next_cursor"] is not None

    second_page = await client.get(
        "/api/v1/public/services",
        params={"limit": 2, "cursor": first_body["next_cursor"]},
        headers=_auth(key),
    )
    second_body = second_page.json()
    assert len(second_body["data"]) == 2
    assert second_body["next_cursor"] is not None

    third_page = await client.get(
        "/api/v1/public/services",
        params={"limit": 2, "cursor": second_body["next_cursor"]},
        headers=_auth(key),
    )
    third_body = third_page.json()
    assert len(third_body["data"]) == 1
    assert third_body["next_cursor"] is None

    all_names = {s["name"] for page in (first_body, second_body, third_body) for s in page["data"]}
    assert all_names == {f"Servicio {i}" for i in range(5)}


async def test_public_conversations_list_and_filter_by_external_user(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Conversaciones Pub", "conv-pub@example.com")
    key = await _create_api_key(client, admin_token, scopes=["chat:write", "conversations:read"])

    await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-1", "message": "hola"},
        headers=_auth(key),
    )
    await client.post(
        "/api/v1/public/chat",
        json={"external_user_id": "user-2", "message": "hola"},
        headers=_auth(key),
    )

    all_conversations = await client.get("/api/v1/public/conversations", headers=_auth(key))
    assert all_conversations.status_code == 200
    assert len(all_conversations.json()["data"]) == 2

    filtered = await client.get(
        "/api/v1/public/conversations",
        params={"external_user_id": "user-1"},
        headers=_auth(key),
    )
    assert len(filtered.json()["data"]) == 1


async def test_public_schedule_endpoint(client: AsyncClient) -> None:
    admin_token = await _register(client, "Empresa Horarios Pub", "schedule-pub@example.com")
    branch = await client.post(
        "/api/v1/admin/branches", json={"name": "Casa Matriz"}, headers=_auth(admin_token)
    )
    branch_id = branch.json()["id"]
    await client.post(
        "/api/v1/admin/business-hours",
        json={"branch_id": branch_id, "day_of_week": 0, "opens_at": "09:00", "closes_at": "18:00"},
        headers=_auth(admin_token),
    )
    await client.post(
        "/api/v1/admin/schedule-exceptions",
        json={"branch_id": branch_id, "exception_date": "2099-01-01", "is_closed": True},
        headers=_auth(admin_token),
    )

    key = await _create_api_key(client, admin_token, scopes=["catalog:read"])
    response = await client.get("/api/v1/public/schedule", headers=_auth(key))
    assert response.status_code == 200
    body = response.json()
    assert len(body["branches"]) == 1
    assert len(body["business_hours"]) == 1
    assert len(body["upcoming_exceptions"]) == 1
