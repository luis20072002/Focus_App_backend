from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, Integer, DateTime
from datetime import datetime


class RankingCycle(Base):
    __tablename__ = "ranking_cycle"

    id_cycle: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ranking_history: Mapped[list["RankingHistory"]] = relationship(back_populates="cycle")