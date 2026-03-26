from app import create_app


def test_login_page_loads():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Iniciar sesi" in response.data


def test_codexia_endpoint_returns_message():
    app = create_app()
    client = app.test_client()

    response = client.get("/codexia")

    assert response.status_code == 200
    assert response.data == b"fue hecho por CodexIA"


def test_protected_page_redirects_without_session():
    app = create_app()
    client = app.test_client()

    response = client.get("/inicio", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
