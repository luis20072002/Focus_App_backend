from typing import Optional
from app.database import Base
from app.models.mixins import CreatedAtMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Date, CheckConstraint, ForeignKey
from datetime import datetime, date


class User(CreatedAtMixin, Base):
    __tablename__ = "user"

    id_user: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    lastname: Mapped[str] = mapped_column(String(50), nullable=False)
    username: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    private_profile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    foints_season: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    foints_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    id_role: Mapped[int] = mapped_column(Integer, ForeignKey("role.id_role"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="user_contact_ck"),
    )

    # Relaciones
    role: Mapped["Role"] = relationship(back_populates="users")

    tasks: Mapped[list["Task"]] = relationship(back_populates="user")

    # Usuarios que este usuario sigue
    following: Mapped[list["Follow"]] = relationship(
        back_populates="follower",
        foreign_keys="Follow.id_follower"
    )
    # Usuarios que siguen a este usuario
    followers: Mapped[list["Follow"]] = relationship(
        back_populates="followed",
        foreign_keys="Follow.id_followed"
    )

    badges: Mapped[list["UserBadge"]] = relationship(back_populates="user")

    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")

    suggestions: Mapped[list["TemplateSuggestion"]] = relationship(
        back_populates="user",
        foreign_keys="TemplateSuggestion.id_user"
    )
    # Sugerencias revisadas por este usuario como admin
    suggestions_reviewed: Mapped[list["TemplateSuggestion"]] = relationship(
        back_populates="admin",
        foreign_keys="TemplateSuggestion.id_admin"
    )

    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user")

    verification_tokens: Mapped[list["VerificationToken"]] = relationship(back_populates="user")

    ranking_history: Mapped[list["RankingHistory"]] = relationship(back_populates="user")
    
    device_tokens: Mapped[list["DeviceToken"]] = relationship(back_populates="user")
    foint_transactions: Mapped[list["FointTransaction"]] = relationship(back_populates="user")