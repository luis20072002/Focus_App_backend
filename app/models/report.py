from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, Integer, DateTime, ForeignKey, Enum
from datetime import datetime
import enum


class ReportStatus(enum.Enum):
    pending = "pendiente"
    reviewed = "revisado"
    resolved = "resuelto"


class Report(Base):
    __tablename__ = "report"

    id_report: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_photo: Mapped[int] = mapped_column(Integer, ForeignKey("confirmation_photo.id_photo"), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), nullable=False, default=ReportStatus.pending)
    id_moderator: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    photo: Mapped["ConfirmationPhoto"] = relationship(back_populates="reports")
    user: Mapped["User"] = relationship(back_populates="reports_sent", foreign_keys=[id_user])
    moderator: Mapped[Optional["User"]] = relationship(back_populates="reports_moderated", foreign_keys=[id_moderator])