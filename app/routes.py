from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from pydantic import ValidationError

from .api_client import ApiClientError, SessionExpiredError, get_api_client
from .auth import login_required, store_session
from .schemas import ForgotPasswordPayload, HistoryFilterPayload, LoginPayload, PackageCreatePayload, ProfilePayload, RegistrationPayload

main = Blueprint("main", __name__)


@main.app_context_processor
def inject_user():
    return {
        "current_user": session.get("api_user"),
        "current_notifications": session.get("api_notifications", []),
    }


@main.before_app_request
def keep_session_synced():
    if request.endpoint in {None, "main.index", "main.login", "main.registro", "main.recuperar", "main.codexia"}:
        return None
    if request.endpoint and request.endpoint.startswith("static"):
        return None
    if "api_token" not in session:
        return None

    try:
        me = get_api_client().me()
        session["api_user"] = me.get("data", {}).get("user", session.get("api_user"))
        notifications = get_api_client().notification_feed()
        session["api_notifications"] = notifications.get("data", {}).get("items", [])
    except SessionExpiredError as error:
        session.clear()
        flash(str(error), "error")
        return redirect(url_for("main.index"))
    except ApiClientError:
        return None


def _flash_validation_error(error: ValidationError | ApiClientError) -> None:
    if isinstance(error, ApiClientError) and error.errors:
        for messages in error.errors.values():
            for message in messages:
                flash(message, "error")
        return

    if isinstance(error, ValidationError):
        for item in error.errors():
            flash(item["msg"], "error")
        return

    flash(str(error), "error")


@main.route("/")
def index():
    if session.get("api_token"):
        return redirect(url_for("main.inicio"))
    return render_template("index.html")


@main.route("/", methods=["POST"])
def login():
    try:
        payload = LoginPayload.model_validate(request.form.to_dict())
        response = get_api_client().login(payload.model_dump())
        store_session(response)
        notifications = get_api_client().notification_feed()
        session["api_notifications"] = notifications.get("data", {}).get("items", [])
        flash("Sesión iniciada correctamente.", "success")
        return redirect(url_for("main.inicio"))
    except (ValidationError, ApiClientError) as error:
        _flash_validation_error(error)
        return render_template("index.html", form=request.form), 422


@main.route("/codexia")
def codexia():
    return "fue hecho por CodexIA"


@main.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("main.index"))


@main.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        try:
            payload = RegistrationPayload.model_validate(request.form.to_dict())
            response = get_api_client().register_client(payload.model_dump(exclude={"password_confirmation"}))
            store_session(response)
            notifications = get_api_client().notification_feed()
            session["api_notifications"] = notifications.get("data", {}).get("items", [])
            flash("Cuenta creada correctamente.", "success")
            return redirect(url_for("main.inicio"))
        except (ValidationError, ApiClientError) as error:
            _flash_validation_error(error)
            return render_template("registro.html", form=request.form), 422
    return render_template("registro.html")


@main.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        try:
            payload = ForgotPasswordPayload.model_validate(request.form.to_dict())
            response = get_api_client().forgot_password(payload.model_dump())
            flash(response.get("message", "Solicitud procesada."), "success")
            token = response.get("data", {}).get("reset_token")
            return render_template("recuperar.html", reset_token=token)
        except (ValidationError, ApiClientError) as error:
            _flash_validation_error(error)
            return render_template("recuperar.html", form=request.form), 422
    return render_template("recuperar.html")


@main.route("/inicio")
@login_required
def inicio():
    try:
        summary = get_api_client().dashboard()
    except ApiClientError as error:
        _flash_validation_error(error)
        summary = {"data": {"totals": {}, "recent_packages": []}}
    return render_template(
        "inicio.html",
        summary=summary.get("data", {}),
        open_modal=request.args.get("open") == "new",
    )


@main.route("/envios")
@login_required
def envios():
    try:
        filters = HistoryFilterPayload.model_validate(
            {
                "search": request.args.get("search"),
                "status": request.args.get("status"),
                "page": request.args.get("page", 1),
            }
        )
        response = get_api_client().my_packages(filters.model_dump())
    except (ValidationError, ApiClientError) as error:
        _flash_validation_error(error)
        response = {"data": {"items": [], "pagination": {"page": 1, "total_pages": 1, "total_items": 0}}}

    return render_template("envios.html", payload=response.get("data", {}))


@main.route("/envios/nuevo", methods=["POST"])
@login_required
def crear_envio():
    try:
        payload = PackageCreatePayload.model_validate(request.form.to_dict())
        get_api_client().create_package(payload.model_dump())
        flash("Envío registrado correctamente.", "success")
    except (ValidationError, ApiClientError) as error:
        _flash_validation_error(error)
        return redirect(url_for("main.inicio", open="new"))

    return redirect(url_for("main.envios"))


@main.route("/envios/<int:package_id>")
@login_required
def detalle_envio(package_id: int):
    try:
        payload = get_api_client().get_package(package_id)
    except ApiClientError as error:
        _flash_validation_error(error)
        return redirect(url_for("main.envios"))
    return render_template("envio_detalle.html", package=payload.get("data", {}))


@main.route("/rastrear", methods=["GET", "POST"])
@login_required
def rastrear():
    tracking_code = request.values.get("tracking_code", "").strip()
    package = None
    if tracking_code:
        try:
            package = get_api_client().track_package(tracking_code).get("data", {})
        except ApiClientError as error:
            _flash_validation_error(error)
    return render_template("rastrear.html", package=package, tracking_code=tracking_code)


@main.route("/historial")
@login_required
def historial():
    try:
        filters = HistoryFilterPayload.model_validate(
            {
                "search": request.args.get("search"),
                "status": request.args.get("status"),
                "start_date": request.args.get("start_date"),
                "end_date": request.args.get("end_date"),
                "page": request.args.get("page", 1),
            }
        )
        payload = get_api_client().my_history(filters.model_dump()).get("data", {})
    except (ValidationError, ApiClientError) as error:
        _flash_validation_error(error)
        payload = {"items": [], "pagination": {"page": 1, "total_pages": 1, "total_items": 0}}
    return render_template("historial.html", payload=payload, filters=request.args)


@main.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    api = get_api_client()
    if request.method == "POST":
        try:
            payload = ProfilePayload.model_validate(request.form.to_dict())
            response = api.update_profile(payload.model_dump())
            current_user = dict(session.get("api_user", {}))
            current_user["client"] = response.get("data", {})
            session["api_user"] = current_user
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for("main.perfil"))
        except (ValidationError, ApiClientError) as error:
            _flash_validation_error(error)
            profile = request.form
            return render_template("perfil.html", profile=profile), 422

    try:
        profile = api.my_profile().get("data", {})
    except ApiClientError as error:
        _flash_validation_error(error)
        profile = {}
    return render_template("perfil.html", profile=profile)
