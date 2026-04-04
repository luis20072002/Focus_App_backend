from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Date, ForeignKey, UniqueConstraint
from datetime import date


class UserBadge(Base):
    __tablename__ = "user_badge"

    id_user_badge: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    id_badge: Mapped[int] = mapped_column(Integer, ForeignKey("badge.id_badge"), nullable=False)
    cycle_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    position_obtained: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_user", "id_badge", "cycle_start_date", name="user_badge_cycle_un"),
    )

    user: Mapped["User"] = relationship(back_populates="badges")
    badge: Mapped["Badge"] = relationship(back_populates="user_badges")