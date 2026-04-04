from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum
from datetime import datetime
import enum


class TokenType(enum.Enum):
    password_recovery = "recuperacion_contrasena"
    account_verification = "verificacion_cuenta"


class TokenSendMethod(enum.Enum):
    email = "correo"
    phone = "telefono"


class VerificationToken(Base):
    __tablename__ = "verification_token"

    id_token: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    type: Mapped[TokenType] = mapped_column(Enum(TokenType), nullable=False)
    send_method: Mapped[TokenSendMethod] = mapped_column(Enum(TokenSendMethod), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="verification_tokens")