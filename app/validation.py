from __future__ import annotations

from typing import Any

FIELD_LABELS: dict[str, str] = {
    "first_name": "nombre",
    "last_name": "apellidos",
    "email": "correo electrónico",
    "password": "contraseña",
    "password_confirmation": "confirmación de contraseña",
    "phone": "teléfono",
    "address": "dirección",
    "description": "descripción",
    "weight": "peso",
    "volume": "volumen",
    "package_type": "tipo de paquete",
    "origin_address": "origen",
    "destination_address": "destino",
    "estimated_delivery_at": "fecha estimada de entrega",
    "start_date": "fecha inicial",
    "end_date": "fecha final",
    "tracking_code": "código de rastreo",
    "search": "búsqueda",
    "status": "estado",
    "page": "página",
}

NON_FIELD_KEYS = {"body", "query", "path", "api", "campo"}


def _field_name(loc: list[Any] | tuple[Any, ...] | None) -> str:
    for item in reversed(loc or []):
        if isinstance(item, str) and item not in {"body", "query", "path"}:
            return item

    return "campo"


def field_label(field_name: str) -> str:
    return FIELD_LABELS.get(field_name, field_name.replace("_", " "))


def infer_field_from_message(message: str) -> str | None:
    normalized = message.strip().lower()

    if "contraseñas no coinciden" in normalized:
        return "password_confirmation"
    if "fecha final debe ser igual o posterior" in normalized:
        return "end_date"
    if "fecha estimada de entrega" in normalized:
        return "estimated_delivery_at"
    if "tracking" in normalized or "rastreo" in normalized:
        return "tracking_code"

    return None


def normalize_error_key(field_name: str | None, message: str) -> str | None:
    if field_name and field_name not in NON_FIELD_KEYS:
        return field_name

    return infer_field_from_message(message)


def translate_validation_error(error: dict[str, Any]) -> dict[str, Any]:
    field_name = _field_name(error.get("loc"))
    label = field_label(field_name)
    error_type = str(error.get("type", ""))
    ctx = error.get("ctx") or {}
    original_message = str(error.get("msg", "")).strip()
    normalized_message = original_message.removeprefix("Value error, ").removeprefix("Assertion failed, ").strip()

    if "email" in field_name and ("email" in error_type or "email" in original_message.lower() or error_type == "value_error"):
        message = f"El campo {label} debe ser un correo electrónico válido."
    elif error_type == "missing":
        message = f"El campo {label} es obligatorio."
    elif error_type == "string_too_short":
        message = f"El campo {label} debe tener al menos {ctx.get('min_length', 1)} caracteres."
    elif error_type == "string_too_long":
        message = f"El campo {label} no puede exceder {ctx.get('max_length', 0)} caracteres."
    elif error_type in {"int_parsing", "int_type"}:
        message = f"El campo {label} debe ser un número entero válido."
    elif error_type in {"float_parsing", "float_type"}:
        message = f"El campo {label} debe ser un número válido."
    elif error_type == "greater_than":
        message = f"El campo {label} debe ser mayor que {ctx.get('gt')}."
    elif error_type == "greater_than_equal":
        message = f"El campo {label} debe ser mayor o igual a {ctx.get('ge')}."
    elif error_type in {"date_parsing", "date_from_datetime_parsing", "date_type"}:
        message = f"El campo {label} debe contener una fecha válida."
    elif error_type in {"datetime_parsing", "datetime_from_date_parsing", "datetime_type"}:
        message = f"El campo {label} debe contener una fecha y hora válidas."
    elif error_type in {"literal_error", "enum"}:
        message = f"El valor seleccionado para {label} no es válido."
    elif normalized_message:
        message = normalized_message
    else:
        message = f"El campo {label} contiene un valor inválido."

    return {
        **error,
        "msg": message,
    }


def translate_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [translate_validation_error(error) for error in errors]


def bucket_errors(errors: list[dict[str, Any]]) -> tuple[dict[str, list[str]], list[str]]:
    field_errors: dict[str, list[str]] = {}
    general_errors: list[str] = []

    for error in errors:
        message = str(error.get("msg", "")).strip()
        raw_field = _field_name(error.get("loc"))
        field_name = normalize_error_key(raw_field, message)

        if field_name and message:
            field_errors.setdefault(field_name, []).append(message)
        elif message:
            general_errors.append(message)

    return field_errors, general_errors


def bucket_error_map(error_map: dict[str, list[str] | str]) -> tuple[dict[str, list[str]], list[str]]:
    field_errors: dict[str, list[str]] = {}
    general_errors: list[str] = []

    for raw_field, messages in error_map.items():
        for message in messages if isinstance(messages, list) else [messages]:
            normalized_message = str(message).strip()
            field_name = normalize_error_key(raw_field, normalized_message)

            if field_name and normalized_message:
                field_errors.setdefault(field_name, []).append(normalized_message)
            elif normalized_message:
                general_errors.append(normalized_message)

    return field_errors, general_errors
