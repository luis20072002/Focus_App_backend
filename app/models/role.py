from app.database import Base

from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text

class Role(Base):
    __tablename__="role"

    id_role: Mapped[int]= mapped_column (primary_key = True, autoincrement=False)
    name_role: Mapped[str]=mapped_column(String(30), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")