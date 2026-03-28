import app.routes as routes

from app import create_app


class StubApiClient:
    def __init__(self) -> None:
        self.created_payload = None
        self.updated_payload = None
        self.profile_updated_payload = None
        self.profile = {
            "id": 1,
            "user_id": 1,
            "first_name": "Cliente",
            "last_name": "Demo",
            "phone": "5551234567",
            "email": "cliente@example.com",
            "address": "Calle demo 123",
            "state": "active",
        }

    def me(self) -> dict:
        return {"data": {"user": {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}}}

    def notification_feed(self) -> dict:
        return {"data": {"items": []}}

    def dashboard(self) -> dict:
        return {"data": {"totals": {}, "recent_packages": []}}

    def create_package(self, payload: dict) -> dict:
        self.created_payload = payload
        return {"message": "ok", "data": {"id": 1}}

    def update_my_package(self, package_id: int, payload: dict) -> dict:
        self.updated_payload = {"package_id": package_id, **payload}
        return {"message": "ok", "data": {"id": package_id, **payload}}

    def get_package(self, package_id: int) -> dict:
        return {
            "data": {
                "id": package_id,
                "tracking_code": "VEY-2026-000001",
                "description": "Caja con documentos",
                "weight": 2.5,
                "volume": 1.2,
                "package_type": "Caja",
                "origin_address": "Origen principal 123",
                "destination_address": "Destino final 456",
                "estimated_delivery_at": None,
                "status": {"name": "Pendiente"},
                "events": [],
            }
        }

    def my_profile(self) -> dict:
        return {"data": dict(self.profile)}

    def update_profile(self, payload: dict) -> dict:
        self.profile_updated_payload = payload
        self.profile.update(payload)
        return {"message": "ok", "data": dict(self.profile)}


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


def test_new_package_serializes_datetime_payload(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    api = StubApiClient()
    monkeypatch.setattr(routes, "get_api_client", lambda: api)

    with client.session_transaction() as flask_session:
        flask_session["api_token"] = "token"
        flask_session["api_user"] = {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}

    response = client.post(
        "/envios/nuevo",
        data={
            "origin_address": "Origen principal 123",
            "destination_address": "Destino final 456",
            "description": "Caja con documentos",
            "package_type": "Caja",
            "weight": "2.50",
            "volume": "1.20",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/envios")
    assert "estimated_delivery_at" not in api.created_payload


def test_history_rejects_invalid_date_range_in_spanish(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    monkeypatch.setattr(routes, "get_api_client", lambda: StubApiClient())

    with client.session_transaction() as flask_session:
        flask_session["api_token"] = "token"
        flask_session["api_user"] = {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}

    response = client.get("/historial?start_date=2026-04-10&end_date=2026-04-01")
    content = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "La fecha final debe ser igual o posterior a la fecha inicial." in content


def test_new_package_modal_shows_visible_labels(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    monkeypatch.setattr(routes, "get_api_client", lambda: StubApiClient())

    with client.session_transaction() as flask_session:
        flask_session["api_token"] = "token"
        flask_session["api_user"] = {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}

    response = client.get("/inicio?open=new")
    content = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Origen" in content
    assert 'name="estimated_delivery_at"' not in content


def test_new_package_validation_renders_inline_error(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    monkeypatch.setattr(routes, "get_api_client", lambda: StubApiClient())

    with client.session_transaction() as flask_session:
        flask_session["api_token"] = "token"
        flask_session["api_user"] = {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}

    response = client.post(
        "/envios/nuevo",
        data={
            "origin_address": "AB",
            "destination_address": "Destino final 456",
            "description": "Caja con documentos",
            "package_type": "Caja",
            "weight": "2.50",
            "volume": "1.20",
        },
    )
    content = response.data.decode("utf-8")

    assert response.status_code == 422
    assert content.count("El campo origen debe tener al menos 3 caracteres.") == 1
    assert "field-error" in content


def test_client_can_edit_own_package(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    api = StubApiClient()
    monkeypatch.setattr(routes, "get_api_client", lambda: api)

    with client.session_transaction() as flask_session:
        flask_session["api_token"] = "token"
        flask_session["api_user"] = {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}

    response = client.post(
        "/envios/10/editar",
        data={
            "origin_address": "Origen editado 123",
            "destination_address": "Destino editado 456",
            "description": "Caja editada",
            "package_type": "Sobre",
            "weight": "4.10",
            "volume": "1.80",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/envios/10")
    assert api.updated_payload["package_id"] == 10
    assert api.updated_payload["origin_address"] == "Origen editado 123"


def test_client_can_update_profile(monkeypatch):
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    api = StubApiClient()
    monkeypatch.setattr(routes, "get_api_client", lambda: api)

    with client.session_transaction() as flask_session:
        flask_session["api_token"] = "token"
        flask_session["api_user"] = {"id": 1, "name": "Cliente Demo", "email": "cliente@example.com"}

    response = client.post(
        "/perfil",
        data={
            "first_name": "Jesus",
            "last_name": "Morales",
            "email": "jesus@example.com",
            "phone": "5559998888",
            "address": "Nueva direccion 456",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/perfil")
    assert api.profile_updated_payload["first_name"] == "Jesus"
    assert api.profile_updated_payload["email"] == "jesus@example.com"

    with client.session_transaction() as flask_session:
        assert flask_session["api_user"]["name"] == "Jesus Morales"
        assert flask_session["api_user"]["email"] == "jesus@example.com"
