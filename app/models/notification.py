from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, Boolean, Integer, DateTime, ForeignKey, Enum
from datetime import datetime
from sqlalchemy.sql import func
import enum


class NotificationType(enum.Enum):
    task_reminder = "recordatorio_tarea"
    task_expired = "tarea_vencida"
    urgent_task = "tarea_urgente"
    new_follower = "nuevo_seguidor"
    suggestion_resolved = "sugerencia_resuelta"


class Notification(Base):
    __tablename__ = "notification"

    id_notification: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    date: Mapped[datetime] = mapped_column(
    DateTime,
    server_default=func.now(),
    nullable=False
)
    id_reference: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="notifications")