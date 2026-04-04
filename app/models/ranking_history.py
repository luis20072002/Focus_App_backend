from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Date, ForeignKey, UniqueConstraint, CheckConstraint
from datetime import date


class RankingHistory(Base):
    __tablename__ = "ranking_history"

    id_history: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    cycle_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    cycle_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    global_position: Mapped[int] = mapped_column(Integer, nullable=False)
    foints_cycle: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_user", "cycle_start_date", name="ranking_history_cycle_un"),
        CheckConstraint("global_position > 0", name="ranking_history_position_ck"),
        CheckConstraint("foints_cycle >= 0", name="ranking_history_foints_ck"),
    )

    user: Mapped["User"] = relationship(back_populates="ranking_history")