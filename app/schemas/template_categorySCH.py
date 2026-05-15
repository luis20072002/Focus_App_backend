from pydantic import BaseModel
from typing import Optional


class TemplateCategoryBase(BaseModel):
    category_name: str
    category_description: Optional[str] = None


class TemplateCategoryCreate(TemplateCategoryBase):
    pass


class TemplateCategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    category_description: Optional[str] = None


class TemplateCategoryResponse(TemplateCategoryBase):
    id_category: int

    model_config = {"from_attributes": True}