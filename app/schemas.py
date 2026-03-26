from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegistrationPayload(BaseModel):
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


class ForgotPasswordPayload(BaseModel):
    email: EmailStr


class PackageCreatePayload(BaseModel):
    description: str = Field(min_length=3, max_length=255)
    weight: float = Field(gt=0)
    volume: float | None = Field(default=None, gt=0)
    package_type: str = Field(min_length=2, max_length=100)
    origin_address: str = Field(min_length=3, max_length=255)
    destination_address: str = Field(min_length=3, max_length=255)
    estimated_delivery_at: datetime | None = None


class ProfilePayload(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)


class HistoryFilterPayload(BaseModel):
    search: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    page: int = 1

    @field_validator("page")
    @classmethod
    def valid_page(cls, value: int) -> int:
        return max(1, value)


class ApiEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: str
    data: dict
