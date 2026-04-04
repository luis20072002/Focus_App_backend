from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Enum
from datetime import datetime
import enum


class PhotoVisibility(enum.Enum):
    global_ = "global"
    friends = "amigos"
    followers = "seguidores"


class ConfirmationPhoto(Base):
    __tablename__ = "confirmation_photo"

    id_photo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_task: Mapped[int] = mapped_column(Integer, ForeignKey("task.id_task"), nullable=False, unique=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    photo_url: Mapped[str] = mapped_column(String(255), nullable=False)
    visibility: Mapped[PhotoVisibility] = mapped_column(Enum(PhotoVisibility), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    task: Mapped["Task"] = relationship(back_populates="confirmation_photo")
    user: Mapped["User"] = relationship(back_populates="confirmation_photos")

    likes: Mapped[list["Like"]] = relationship(back_populates="photo")
    reports: Mapped[list["Report"]] = relationship(back_populates="photo")