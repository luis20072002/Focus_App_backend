from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime, date


class UserBase(BaseModel):
    name: str
    lastname: str
    username: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birth_date: date
    profile_picture: Optional[str] = None
    description: Optional[str] = None
    private_profile: bool = False

    @model_validator(mode="after")
    def email_or_phone_required(self) -> "UserBase":
        if self.email is None and self.phone is None:
            raise ValueError("Se requiere al menos un correo o un número de teléfono")
        return self


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    lastname: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    profile_picture: Optional[str] = None
    description: Optional[str] = None
    private_profile: Optional[bool] = None
    password: Optional[str] = None

    @model_validator(mode="after")
    def validate_contact_info(self):
        # Solo bloquea el caso explícito:
        # PATCH enviando ambos en null

        if self.email is None and self.phone is None:
            provided_fields = self.model_fields_set

            if "email" in provided_fields and "phone" in provided_fields:
                raise ValueError(
                    "No puedes eliminar correo y teléfono simultáneamente"
                )

        return self


class UserResponse(UserBase):
    id_user: int
    foints_season: int
    foints_total: int
    id_role: int
    created_at: datetime
    active: bool

    model_config = {"from_attributes": True}