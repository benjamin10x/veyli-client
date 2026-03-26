from __future__ import annotations

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "api_token" not in session:
            flash("Debes iniciar sesión para continuar.", "error")
            return redirect(url_for("main.index"))
        return view(*args, **kwargs)

    return wrapper


def store_session(auth_response: dict) -> None:
    session["api_token"] = auth_response["data"]["tokens"]["access_token"]
    session["api_refresh_token"] = auth_response["data"]["tokens"]["refresh_token"]
    session["api_user"] = auth_response["data"]["user"]
