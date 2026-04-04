from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, CheckConstraint


class Badge(Base):
    __tablename__ = "badge"

    id_badge: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    min_position: Mapped[int] = mapped_column(Integer, nullable=False)
    max_position: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("min_position <= max_position", name="badge_position_ck"),
    )

    user_badges: Mapped[list["UserBadge"]] = relationship(back_populates="badge")