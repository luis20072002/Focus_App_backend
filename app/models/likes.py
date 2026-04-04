from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime


class Like(Base):
    __tablename__ = "likes"

    id_like: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_photo: Mapped[int] = mapped_column(Integer, ForeignKey("confirmation_photo.id_photo"), nullable=False)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey("user.id_user"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_photo", "id_user", name="likes_id_photo_id_user_un"),
    )

    photo: Mapped["ConfirmationPhoto"] = relationship(back_populates="likes")
    user: Mapped["User"] = relationship(back_populates="likes")