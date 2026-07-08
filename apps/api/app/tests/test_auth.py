def _register_user(
    client,
    *,
    email: str = "auth-user@tradepilot.in",
    password: str = "StrongPass123",
    full_name: str = "Auth User",
    **extra_fields,
):
    payload = {
        "email": email,
        "password": password,
        "full_name": full_name,
        **extra_fields,
    }
    return client.post("/auth/register", json=payload)


def _login_user(
    client,
    *,
    email: str = "auth-user@tradepilot.in",
    password: str = "StrongPass123",
):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


def test_user_can_register(client) -> None:
    response = _register_user(client, email="register@tradepilot.in")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "register@tradepilot.in"
    assert body["full_name"] == "Auth User"


def test_user_can_login(client) -> None:
    register_response = _register_user(client, email="login@tradepilot.in")
    assert register_response.status_code == 201

    response = _login_user(client, email="login@tradepilot.in")

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "login@tradepilot.in"


def test_auth_me_works_with_token(client) -> None:
    register_response = _register_user(client, email="me@tradepilot.in")
    assert register_response.status_code == 201

    login_response = _login_user(client, email="me@tradepilot.in")
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@tradepilot.in"
    assert body["is_active"] is True


def test_auth_me_fails_without_token(client) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Authentication required"
    assert body["error_code"] == "http_401"
    assert body["request_id"].startswith("req_")


def test_register_does_not_enable_live_trading(client) -> None:
    response = _register_user(
        client,
        email="live-disabled@tradepilot.in",
        live_trading_enabled=True,
    )

    assert response.status_code == 201
    assert response.json()["live_trading_enabled"] is False


def test_register_does_not_enable_auto_trading(client) -> None:
    response = _register_user(
        client,
        email="auto-disabled@tradepilot.in",
        auto_trading_enabled=True,
    )

    assert response.status_code == 201
    assert response.json()["auto_trading_enabled"] is False


def test_password_is_not_returned_in_api_responses(client) -> None:
    register_response = _register_user(client, email="password-hidden@tradepilot.in")
    assert register_response.status_code == 201
    assert "hashed_password" not in register_response.json()
    assert "password" not in register_response.json()

    login_response = _login_user(client, email="password-hidden@tradepilot.in")
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert "hashed_password" not in login_body["user"]
    assert "password" not in login_body["user"]

    token = login_body["access_token"]
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert "hashed_password" not in me_response.json()
    assert "password" not in me_response.json()
