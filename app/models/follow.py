from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from datetime import datetime


class Follow(Base):
    __tablename__ = "follow"

    id_follow: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_follower: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    id_followed: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_follower", "id_followed", name="follow_id_follower_id_followed_un"),
        CheckConstraint("id_follower <> id_followed", name="follow_no_self_follow_ck"),
    )

    follower: Mapped["User"] = relationship(back_populates="following", foreign_keys=[id_follower])
    followed: Mapped["User"] = relationship(back_populates="followers", foreign_keys=[id_followed])