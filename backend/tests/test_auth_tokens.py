from httpx import AsyncClient


async def _register(client: AsyncClient, company_name: str, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/admin/auth/register",
        json={"company_name": company_name, "admin_email": email, "admin_password": "s3cret-pass"},
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


async def test_refresh_rotates_and_invalidates_old_token(client: AsyncClient) -> None:
    tokens = await _register(client, "Empresa Refresh", "refresh@example.com")

    first_refresh = await client.post(
        "/api/v1/admin/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert first_refresh.status_code == 200
    new_tokens = first_refresh.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # El refresh token original ya fue usado (rotación de un solo uso).
    reuse_attempt = await client.post(
        "/api/v1/admin/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_attempt.status_code == 401

    # El nuevo sí sirve.
    second_refresh = await client.post(
        "/api/v1/admin/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert second_refresh.status_code == 200


async def test_logout_invalidates_refresh_token(client: AsyncClient) -> None:
    tokens = await _register(client, "Empresa Logout", "logout@example.com")

    logout_response = await client.post(
        "/api/v1/admin/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_attempt = await client.post(
        "/api/v1/admin/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_attempt.status_code == 401


async def test_logout_is_idempotent_for_garbage_input(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/auth/logout", json={"refresh_token": "not-a-real-token"}
    )
    assert response.status_code == 204


async def test_logout_does_not_affect_other_tenants(client: AsyncClient) -> None:
    tokens_a = await _register(client, "Empresa Logout A", "logout-a@example.com")
    tokens_b = await _register(client, "Empresa Logout B", "logout-b@example.com")

    await client.post(
        "/api/v1/admin/auth/logout", json={"refresh_token": tokens_a["refresh_token"]}
    )

    still_valid = await client.post(
        "/api/v1/admin/auth/refresh", json={"refresh_token": tokens_b["refresh_token"]}
    )
    assert still_valid.status_code == 200
