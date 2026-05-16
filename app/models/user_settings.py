from typing import Optional
from app.database import Base
from app.models.mixins import TimestampMixin  # <-- import
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Text, Boolean, Integer, String, ForeignKey, Enum
import enum


class ThemeType(enum.Enum):
    light = "claro"
    dark = "oscuro"


class UserSettings(TimestampMixin, Base):  # <-- herencia
    __tablename__ = "user_settings"

    id_settings: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False, unique=True)
    notif_push: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notif_task_reminder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notif_task_expired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notif_urgent_task: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notif_new_follower: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notif_suggestion_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notif_reminder_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    theme: Mapped[ThemeType] = mapped_column(Enum(ThemeType), nullable=False, default=ThemeType.light)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="es")
    app_purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referred_by_friend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # updated_at ya no va aquí, viene del mixin

    user: Mapped["User"] = relationship(back_populates="settings")