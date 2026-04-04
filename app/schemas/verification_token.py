from pydantic import BaseModel
from datetime import datetime
from app.models.verification_token import TokenType, TokenSendMethod


class VerificationTokenBase(BaseModel):
    type: TokenType
    send_method: TokenSendMethod


class VerificationTokenCreate(VerificationTokenBase):
    pass  # id_user se obtiene del token JWT, el token lo genera el backend


class VerificationTokenVerify(BaseModel):
    token: str  # El codigo que el usuario recibe y escribe en la app


class VerificationTokenResponse(VerificationTokenBase):
    id_token: int
    id_user: int
    used: bool
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}