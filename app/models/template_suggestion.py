from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, Integer, DateTime, ForeignKey, Enum
from datetime import datetime
import enum


class SuggestionType(enum.Enum):
    task = "tarea"
    category = "categoria"


class SuggestionStatus(enum.Enum):
    pending = "pendiente"
    approved = "aprobada"
    rejected = "rechazada"


class TemplateSuggestion(Base):
    __tablename__ = "template_suggestion"

    id_suggestion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    type: Mapped[SuggestionType] = mapped_column(Enum(SuggestionType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SuggestionStatus] = mapped_column(Enum(SuggestionStatus), nullable=False, default=SuggestionStatus.pending)
    id_admin: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="suggestions", foreign_keys=[id_user])
    admin: Mapped[Optional["User"]] = relationship(back_populates="suggestions_reviewed", foreign_keys=[id_admin])