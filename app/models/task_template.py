from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, CheckConstraint


class TaskTemplate(Base):
    __tablename__ = "task_template"

    id_task_template: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_category: Mapped[int] = mapped_column(Integer, ForeignKey("template_category.id_category"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    foints_base: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("foints_base > 0", name="task_template_foints_base_ck"),
    )

    category: Mapped["TemplateCategory"] = relationship(back_populates="tasks_template")

    tasks: Mapped[list["Task"]] = relationship(back_populates="task_template")