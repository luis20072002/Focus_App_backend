from pydantic import BaseModel, field_validator
from datetime import datetime
from app.models.verification_token import TokenType, TokenSendMethod


class VerificationTokenBase(BaseModel):
    type: TokenType
    send_method: TokenSendMethod


class VerificationTokenCreate(VerificationTokenBase):
    pass  # id_user se obtiene del token JWT, el token lo genera el backend


class VerificationTokenVerify(BaseModel):
    token: str  # El codigo que el usuario recibe y escribe en la app


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class VerificationTokenResponse(VerificationTokenBase):
    id_token: int
    id_user: int
    used: bool
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}