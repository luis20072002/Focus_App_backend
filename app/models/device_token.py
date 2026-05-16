from app.database import Base
from app.models.mixins import CreatedAtMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum
from datetime import datetime
import enum


class DevicePlatform(enum.Enum):
    android = "android"
    ios = "ios"


class DeviceToken(CreatedAtMixin, Base):
    __tablename__ = "device_token"

    id_device: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    platform: Mapped[DevicePlatform] = mapped_column(Enum(DevicePlatform), nullable=False)

    user: Mapped["User"] = relationship(back_populates="device_tokens")