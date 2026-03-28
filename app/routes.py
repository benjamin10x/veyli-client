from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from pydantic import ValidationError

from .api_client import ApiClientError, SessionExpiredError, get_api_client
from .auth import login_required, store_session
from .schemas import ForgotPasswordPayload, HistoryFilterPayload, LoginPayload, PackageCreatePayload, PackageUpdatePayload, ProfilePayload, RegistrationPayload
from .validation import bucket_error_map, bucket_errors, translate_validation_errors

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


def _flash_messages(messages: list[str]) -> None:
    for message in messages:
        flash(message, "error")


def _validation_feedback(error: ValidationError | ApiClientError) -> tuple[dict[str, list[str]], list[str]]:
    if isinstance(error, ApiClientError):
        field_errors, general_errors = bucket_error_map(error.errors)

        if not field_errors and not general_errors:
            general_errors = [str(error)]

        return field_errors, general_errors

    if isinstance(error, ValidationError):
        return bucket_errors(translate_validation_errors(error.errors()))

    return {}, [str(error)]


def _load_dashboard_summary() -> dict:
    try:
        return get_api_client().dashboard().get("data", {})
    except ApiClientError as error:
        _, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        return {"totals": {}, "recent_packages": []}


def _package_form_data(package: dict | None) -> dict:
    package = package or {}

    return {
        "origin_address": package.get("origin_address", ""),
        "destination_address": package.get("destination_address", ""),
        "description": package.get("description", ""),
        "package_type": package.get("package_type", ""),
        "weight": package.get("weight", ""),
        "volume": package.get("volume", ""),
    }


def _profile_form_data(profile: dict | None) -> dict:
    profile = profile or {}

    return {
        "first_name": profile.get("first_name", ""),
        "last_name": profile.get("last_name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "address": profile.get("address", ""),
    }


@main.route("/")
def index():
    if session.get("api_token"):
        return redirect(url_for("main.inicio"))
    return render_template("index.html")


@main.route("/", methods=["POST"])
def login():
    try:
        payload = LoginPayload.model_validate(request.form.to_dict())
        response = get_api_client().login(payload.model_dump(mode="json"))
        store_session(response)
        notifications = get_api_client().notification_feed()
        session["api_notifications"] = notifications.get("data", {}).get("items", [])
        flash("Sesión iniciada correctamente.", "success")
        return redirect(url_for("main.inicio"))
    except (ValidationError, ApiClientError) as error:
        errors, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        return render_template("index.html", form=request.form, errors=errors), 422


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
            response = get_api_client().register_client(payload.model_dump(mode="json", exclude={"password_confirmation"}))
            store_session(response)
            notifications = get_api_client().notification_feed()
            session["api_notifications"] = notifications.get("data", {}).get("items", [])
            flash("Cuenta creada correctamente.", "success")
            return redirect(url_for("main.inicio"))
        except (ValidationError, ApiClientError) as error:
            errors, general_errors = _validation_feedback(error)
            _flash_messages(general_errors)
            return render_template("registro.html", form=request.form, errors=errors), 422
    return render_template("registro.html")


@main.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        try:
            payload = ForgotPasswordPayload.model_validate(request.form.to_dict())
            response = get_api_client().forgot_password(payload.model_dump(mode="json"))
            flash(response.get("message", "Solicitud procesada."), "success")
            token = response.get("data", {}).get("reset_token")
            return render_template("recuperar.html", reset_token=token)
        except (ValidationError, ApiClientError) as error:
            errors, general_errors = _validation_feedback(error)
            _flash_messages(general_errors)
            return render_template("recuperar.html", form=request.form, errors=errors), 422
    return render_template("recuperar.html")


@main.route("/inicio")
@login_required
def inicio():
    return render_template(
        "inicio.html",
        summary=_load_dashboard_summary(),
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
        response = get_api_client().my_packages(filters.model_dump(mode="json", exclude_none=True))
    except (ValidationError, ApiClientError) as error:
        errors, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        response = {"data": {"items": [], "pagination": {"page": 1, "total_pages": 1, "total_items": 0}}}
        return render_template("envios.html", payload=response.get("data", {}), errors=errors)

    return render_template("envios.html", payload=response.get("data", {}), errors={})


@main.route("/envios/nuevo", methods=["POST"])
@login_required
def crear_envio():
    try:
        payload = PackageCreatePayload.model_validate(request.form.to_dict())
        get_api_client().create_package(payload.model_dump(mode="json", exclude_none=True))
        flash("Envío registrado correctamente.", "success")
    except (ValidationError, ApiClientError) as error:
        errors, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        return render_template(
            "inicio.html",
            summary=_load_dashboard_summary(),
            open_modal=True,
            form=request.form,
            errors=errors,
        ), 422

    return redirect(url_for("main.envios"))


@main.route("/envios/<int:package_id>")
@login_required
def detalle_envio(package_id: int):
    try:
        payload = get_api_client().get_package(package_id)
    except ApiClientError as error:
        _, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        return redirect(url_for("main.envios"))
    package = payload.get("data", {})
    return render_template(
        "envio_detalle.html",
        package=package,
        edit_mode=request.args.get("edit") == "1",
        form=_package_form_data(package),
        errors={},
    )


@main.route("/envios/<int:package_id>/editar", methods=["POST"])
@login_required
def editar_envio(package_id: int):
    api = get_api_client()

    try:
        payload = PackageUpdatePayload.model_validate(request.form.to_dict())
        api.update_my_package(package_id, payload.model_dump(mode="json", exclude_none=True))
        flash("Envío actualizado correctamente.", "success")
        return redirect(url_for("main.detalle_envio", package_id=package_id))
    except (ValidationError, ApiClientError) as error:
        errors, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)

        try:
            package = api.get_package(package_id).get("data", {})
        except ApiClientError as lookup_error:
            _, lookup_general_errors = _validation_feedback(lookup_error)
            _flash_messages(lookup_general_errors)
            return redirect(url_for("main.envios"))

        return render_template(
            "envio_detalle.html",
            package=package,
            edit_mode=True,
            form=request.form,
            errors=errors,
        ), 422


@main.route("/rastrear", methods=["GET", "POST"])
@login_required
def rastrear():
    tracking_code = request.values.get("tracking_code", "").strip()
    package = None
    if tracking_code:
        try:
            package = get_api_client().track_package(tracking_code).get("data", {})
        except ApiClientError as error:
            errors, general_errors = _validation_feedback(error)
            _flash_messages(general_errors)
            return render_template("rastrear.html", package=package, tracking_code=tracking_code, errors=errors)
    return render_template("rastrear.html", package=package, tracking_code=tracking_code, errors={})


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
        payload = get_api_client().my_history(filters.model_dump(mode="json", exclude_none=True)).get("data", {})
    except (ValidationError, ApiClientError) as error:
        errors, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        payload = {"items": [], "pagination": {"page": 1, "total_pages": 1, "total_items": 0}}
        return render_template("historial.html", payload=payload, filters=request.args, errors=errors)
    return render_template("historial.html", payload=payload, filters=request.args, errors={})


@main.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    api = get_api_client()
    if request.method == "POST":
        try:
            payload = ProfilePayload.model_validate(request.form.to_dict())
            response = api.update_profile(payload.model_dump(mode="json", exclude_none=True))
            updated_profile = response.get("data", {})
            current_user = dict(session.get("api_user", {}))
            current_user["client"] = updated_profile
            current_user["name"] = f"{updated_profile.get('first_name', '')} {updated_profile.get('last_name', '')}".strip() or current_user.get("name")
            current_user["email"] = updated_profile.get("email", current_user.get("email"))
            session["api_user"] = current_user
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for("main.perfil"))
        except (ValidationError, ApiClientError) as error:
            errors, general_errors = _validation_feedback(error)
            _flash_messages(general_errors)
            profile = _profile_form_data(request.form.to_dict())
            return render_template("perfil.html", profile=profile, errors=errors), 422

    try:
        profile = _profile_form_data(api.my_profile().get("data", {}))
    except ApiClientError as error:
        _, general_errors = _validation_feedback(error)
        _flash_messages(general_errors)
        profile = _profile_form_data({})
    return render_template("perfil.html", profile=profile, errors={})
