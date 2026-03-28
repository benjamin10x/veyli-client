from datetime import date
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def _allows_none(annotation: Any) -> bool:
    return type(None) in get_args(annotation)


class AppBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_strings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        normalized: dict[str, Any] = {}

        for key, value in data.items():
            field = cls.model_fields.get(key)

            if isinstance(value, str):
                value = value.strip()

                if value == "" and field and _allows_none(field.annotation):
                    normalized[key] = None
                    continue

            normalized[key] = value

        return normalized


class LoginPayload(AppBaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegistrationPayload(AppBaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirmation:
            raise ValueError("Las contraseñas no coinciden.")
        return self


class ForgotPasswordPayload(AppBaseModel):
    email: EmailStr


class PackageCreatePayload(AppBaseModel):
    description: str = Field(min_length=3, max_length=255)
    weight: float = Field(gt=0)
    volume: float | None = Field(default=None, gt=0)
    package_type: str = Field(min_length=2, max_length=100)
    origin_address: str = Field(min_length=3, max_length=255)
    destination_address: str = Field(min_length=3, max_length=255)


class PackageUpdatePayload(AppBaseModel):
    description: str = Field(min_length=3, max_length=255)
    weight: float = Field(gt=0)
    volume: float | None = Field(default=None, gt=0)
    package_type: str = Field(min_length=2, max_length=100)
    origin_address: str = Field(min_length=3, max_length=255)
    destination_address: str = Field(min_length=3, max_length=255)


class ProfilePayload(AppBaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)


class HistoryFilterPayload(AppBaseModel):
    search: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    page: int = 1

    @field_validator("page")
    @classmethod
    def valid_page(cls, value: int) -> int:
        return max(1, value)

    @field_validator("end_date")
    @classmethod
    def valid_date_range(cls, value: date | None, info) -> date | None:
        start_date = info.data.get("start_date")

        if value and start_date and value < start_date:
            raise ValueError("La fecha final debe ser igual o posterior a la fecha inicial.")

        return value


class ApiEnvelope(AppBaseModel):
    model_config = ConfigDict(extra="allow")

    message: str
    data: dict
