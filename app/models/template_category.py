from typing import Optional
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Date, CheckConstraint
from datetime import datetime, date

class TemplateCategory (Base):
    __tablename__="template_category"

    id_category: Mapped[int]=mapped_column(primary_key=True)
    category_name: Mapped[str]=mapped_column(String(80), nullable= False)
    category_description: Mapped[Optional[str]]=mapped_column(Text, nullable= True)

    tasks_template: Mapped[list["TaskTemplate"]] = relationship(back_populates='category')
