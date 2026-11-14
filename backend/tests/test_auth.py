from app.main import ensure_default_user


def register(client, email="a@example.com", password="Passw0rdSolide", name="Dr A"):
    return client.post("/api/auth/register", json={"email": email, "password": password, "full_name": name})


def test_register_sets_secure_session_cookies(client):
    r = register(client)
    assert r.status_code == 201
    assert "password" not in r.text and "hash" not in r.text
    cookies = r.headers.get_list("set-cookie")
    session = next(c for c in cookies if c.startswith("mediai_session="))
    assert "HttpOnly" in session and "SameSite=lax" in session
    csrf = next(c for c in cookies if c.startswith("mediai_csrf="))
    assert "HttpOnly" not in csrf
    assert client.get("/api/auth/me").json()["email"] == "a@example.com"


def test_email_is_case_insensitive_and_unique(client):
    assert register(client, "Dup@Example.com").status_code == 201
    client.cookies.clear()
    assert register(client, "dup@example.com").status_code == 409


def test_weak_password_rejected_without_echo(client):
    r = register(client, password="motdepasse")
    assert r.status_code == 422
    assert "motdepasse" not in r.text


def test_html_in_name_rejected(client):
    assert register(client, name="<script>alert(1)</script>").status_code == 422


def test_unknown_fields_rejected(client):
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": "Passw0rdSolide",
                                                 "full_name": "X", "role": "admin"})
    assert r.status_code == 422


def test_login_success_and_generic_failure(client):
    register(client)
    client.cookies.clear()
    bad_pw = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong"})
    no_user = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "wrong"})
    assert bad_pw.status_code == no_user.status_code == 401
    assert bad_pw.json() == no_user.json()  # no account enumeration
    ok = client.post("/api/auth/login", json={"email": "A@EXAMPLE.COM", "password": "Passw0rdSolide"})
    assert ok.status_code == 200


def test_account_lockout_after_repeated_failures(client):
    register(client)
    client.cookies.clear()
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong"})
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "Passw0rdSolide"})
    assert r.status_code == 401  # locked even with the right password


def test_login_rate_limited(client):
    for _ in range(10):
        client.post("/api/auth/login", json={"email": "z@example.com", "password": "x"})
    r = client.post("/api/auth/login", json={"email": "z@example.com", "password": "x"})
    assert r.status_code == 429 and "retry-after" in r.headers


def test_sql_injection_in_login_is_inert(client):
    register(client)
    client.cookies.clear()
    for payload in ["a@example.com' OR '1'='1", "' OR 1=1 --@x.com"]:
        r = client.post("/api/auth/login", json={"email": payload, "password": "' OR '1'='1"})
        assert r.status_code in (401, 422)


def test_protected_routes_require_auth(client):
    for method, path in [("get", "/api/auth/me"), ("get", "/api/analyses"), ("get", "/api/stats"),
                         ("get", "/api/conversations"), ("post", "/api/conversations")]:
        assert getattr(client, method)(path).status_code == 401, path


def test_forged_session_cookie_rejected(client):
    client.cookies.set("mediai_session", "forged-token")
    assert client.get("/api/auth/me").status_code == 401


def test_csrf_required_on_state_changing_requests(make_user):
    c = make_user()
    token = c.headers.pop("X-CSRF-Token")
    assert c.post("/api/conversations", json={}).status_code == 403
    c.headers["X-CSRF-Token"] = "wrong"
    assert c.post("/api/conversations", json={}).status_code == 403
    c.headers["X-CSRF-Token"] = token
    assert c.post("/api/conversations", json={}).status_code == 201


def test_logout_revokes_session_server_side(make_user):
    c = make_user()
    stolen = c.cookies.get("mediai_session")
    assert c.post("/api/auth/logout").status_code == 204
    c.cookies.set("mediai_session", stolen)  # replaying the old cookie must fail
    assert c.get("/api/auth/me").status_code == 401


def test_delete_account_erases_data(make_user):
    c = make_user()
    c.post("/api/analyses", data={"data": '{"symptoms": "fièvre"}'})
    assert c.delete("/api/auth/me").status_code == 204
    c.cookies.clear()
    r = c.post("/api/auth/login", json={"email": "doc@example.com", "password": "Passw0rdSolide"})
    assert r.status_code == 401


def test_default_account_seeded_once(client):
    ensure_default_user()
    ensure_default_user()
    r = client.post("/api/auth/login", json={"email": "seed@example.com", "password": "SeedPassw0rd!"})
    assert r.status_code == 200 and r.json()["role"] == "admin"
