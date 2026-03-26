from __future__ import annotations

from dataclasses import dataclass

import requests
from flask import current_app, session


class ApiClientError(Exception):
    def __init__(self, message: str, status_code: int = 500, errors: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or {}


class SessionExpiredError(ApiClientError):
    pass


@dataclass
class ApiClient:
    base_url: str
    timeout: int

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        token = session.get("api_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None) -> dict:
        response = requests.request(
            method=method,
            url=f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
            json=json,
            params={key: value for key, value in (params or {}).items() if value not in (None, "")},
            timeout=self.timeout,
            headers=self._headers(),
        )

        try:
            payload = response.json()
        except ValueError:
            payload = {"message": "Respuesta inválida de la API.", "detail": "Invalid JSON"}

        if response.ok:
            return payload

        if response.status_code == 401:
            raise SessionExpiredError("Tu sesión expiró. Inicia sesión nuevamente.", 401)

        detail = payload.get("detail") or payload.get("message") or "La API devolvió un error."
        errors = {}
        if isinstance(detail, list):
            for error in detail:
                field = (error.get("loc") or ["api"])[-1]
                errors.setdefault(field, []).append(error.get("msg", "Valor inválido"))
            detail = "Se encontraron errores de validación."

        raise ApiClientError(str(detail), response.status_code, errors)

    def login(self, payload: dict) -> dict:
        return self.request("POST", "/auth/login", json=payload)

    def register_client(self, payload: dict) -> dict:
        return self.request("POST", "/auth/register/client", json=payload)

    def forgot_password(self, payload: dict) -> dict:
        return self.request("POST", "/auth/forgot-password", json=payload)

    def me(self) -> dict:
        return self.request("GET", "/auth/me")

    def notification_feed(self) -> dict:
        return self.request("GET", "/settings/notifications/feed")

    def dashboard(self) -> dict:
        return self.request("GET", "/dashboard/summary")

    def my_packages(self, params: dict | None = None) -> dict:
        return self.request("GET", "/clients/me/packages", params=params)

    def my_history(self, params: dict | None = None) -> dict:
        return self.request("GET", "/clients/me/packages/history", params=params)

    def create_package(self, payload: dict) -> dict:
        return self.request("POST", "/clients/me/packages", json=payload)

    def get_package(self, package_id: int) -> dict:
        return self.request("GET", f"/packages/{package_id}")

    def track_package(self, tracking_code: str) -> dict:
        return self.request("GET", f"/packages/tracking/{tracking_code}")

    def my_profile(self) -> dict:
        return self.request("GET", "/clients/me/profile")

    def update_profile(self, payload: dict) -> dict:
        return self.request("PUT", "/clients/me/profile", json=payload)


def get_api_client() -> ApiClient:
    return ApiClient(
        base_url=current_app.config["API_BASE_URL"],
        timeout=current_app.config["API_TIMEOUT"],
    )
