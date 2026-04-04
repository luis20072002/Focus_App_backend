from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Enum
from datetime import datetime
import enum


class TaskNotificationType(enum.Enum):
    push = "push"
    email = "email"
    none = "ninguna"


class TaskStatus(enum.Enum):
    pending = "pendiente"
    in_progress = "en_progreso"
    done = "realizada"
    expired = "vencida"


class Task(Base):
    __tablename__ = "task"

    id_task: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    id_task_template: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("task_template.id_task_template"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notification_type: Mapped[TaskNotificationType] = mapped_column(Enum(TaskNotificationType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False)
    foints_earned: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("foints_earned IS NULL OR foints_earned >= 0", name="task_foints_earned_ck"),
    )

    user: Mapped["User"] = relationship(back_populates="tasks")
    task_template: Mapped[Optional["TaskTemplate"]] = relationship(back_populates="tasks")
    confirmation_photo: Mapped[Optional["ConfirmationPhoto"]] = relationship(back_populates="task")