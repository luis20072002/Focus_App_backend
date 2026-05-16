from typing import Optional
from app.database import Base
from app.models.mixins import CreatedAtMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Date, ForeignKey, CheckConstraint, Enum
from datetime import datetime, date
import enum


class TaskNotificationType(enum.Enum):
    push = "push"
    none = "ninguna"


class TaskStatus(enum.Enum):
    pending = "pendiente"
    in_progress = "en_progreso"
    done = "realizada"
    expired = "vencida"


class TaskRecurrenceType(enum.Enum):
    none = "ninguna"
    daily = "diaria"
    weekly = "semanal"
    custom = "personalizada"


class Task(CreatedAtMixin, Base):
    __tablename__ = "task"

    id_task: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    # RF-B06: máximo 3 tareas diarias con is_foint_candidate=True por usuario.
    # Las tareas urgentes (is_urgent=True) no pueden ser candidatas.
    # Esta regla se valida en el endpoint, no como constraint de BD.
    is_foint_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    id_task_template: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("task_template.id_task_template"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notification_type: Mapped[TaskNotificationType] = mapped_column(Enum(TaskNotificationType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False)
    foints_earned: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Se asigna en el endpoint al marcar como realizada

    # Campos de recurrencia
    is_recurrent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurrence_type: Mapped[TaskRecurrenceType] = mapped_column(
        Enum(TaskRecurrenceType), nullable=False, default=TaskRecurrenceType.none
    )
    # Dias de recurrencia: string con dias separados por coma (1=lunes ... 7=domingo)
    # Ejemplo: "1,3,5" = lunes, miercoles, viernes
    recurrence_days: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recurrence_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("foints_earned IS NULL OR foints_earned >= 0", name="task_foints_earned_ck"),
        CheckConstraint(
            "(is_foint_candidate = FALSE) OR (id_task_template IS NOT NULL)",
            name="task_foint_candidate_requires_template_ck"
        ),
    )

    # Relaciones
    user: Mapped["User"] = relationship(back_populates="tasks")
    task_template: Mapped[Optional["TaskTemplate"]] = relationship(back_populates="tasks")
    foint_transactions: Mapped[list["FointTransaction"]] = relationship(back_populates="task")