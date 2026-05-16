from typing import Optional
from app.database import Base
from app.models.mixins import CreatedAtMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, DateTime, ForeignKey, Enum, CheckConstraint
from datetime import datetime
import enum


class FointReason(enum.Enum):
    task_completed = "tarea_completada"
    time_decay = "decremento_tiempo"
    cycle_reset = "reinicio_ciclo"
    manual_adjustment = "ajuste_manual"


class FointTransaction(CreatedAtMixin, Base):
    __tablename__ = "foint_transaction"

    id_transaction: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    id_task: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("task.id_task"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Puede ser negativo
    reason: Mapped[FointReason] = mapped_column(Enum(FointReason), nullable=False)

    __table_args__ = (
        CheckConstraint("amount != 0", name="foint_transaction_amount_not_zero_ck"),
    )

    user: Mapped["User"] = relationship(back_populates="foint_transactions")
    task: Mapped[Optional["Task"]] = relationship(back_populates="foint_transactions")