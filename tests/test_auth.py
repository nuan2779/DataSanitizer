from backend.database import fetch_one


def test_register_login_me_and_logout(isolated_client):
    client = isolated_client

    registered = client.post(
        "/api/auth/register",
        json={
            "username": "phuc_ds",
            "email": "phuc@example.com",
            "password": "StrongPass123",
        },
    )
    assert registered.status_code == 201, registered.text
    payload = registered.json()
    assert payload["user"]["username"] == "phuc_ds"
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert "password" not in payload["user"]

    cookie = registered.headers.get("set-cookie", "").lower()
    assert "datasanitizer_session=" in cookie
    assert "httponly" in cookie

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "phuc@example.com"

    logged_out = client.post("/api/auth/logout")
    assert logged_out.status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    logged_in = client.post(
        "/api/auth/login",
        json={"identifier": "PHUC_DS", "password": "StrongPass123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    assert client.get("/api/auth/me").status_code == 200


def test_register_rejects_duplicate_and_weak_password(isolated_client):
    client = isolated_client
    payload = {
        "username": "phuc_ds",
        "email": "phuc@example.com",
        "password": "StrongPass123",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409

    weak = client.post(
        "/api/auth/register",
        json={"username": "another_user", "email": "another@example.com", "password": "123"},
    )
    assert weak.status_code == 422


def test_password_is_stored_as_hash(isolated_client):
    response = isolated_client.post(
        "/api/auth/register",
        json={"username": "secure_user", "email": "secure@example.com", "password": "NotPlainText123"},
    )
    assert response.status_code == 201
    user = fetch_one("SELECT password_hash, salt FROM users WHERE email = ?", ("secure@example.com",))
    assert user["password_hash"] != "NotPlainText123"
    assert len(user["salt"]) >= 32
