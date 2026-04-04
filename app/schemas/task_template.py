from pydantic import BaseModel, field_validator
from typing import Optional


class TaskTemplateBase(BaseModel):
    id_category: int
    name: str
    description: Optional[str] = None
    foints_base: int
    active: bool = True

    @field_validator("foints_base")
    @classmethod
    def foints_base_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("foints_base debe ser mayor que 0")
        return v


class TaskTemplateCreate(TaskTemplateBase):
    pass


class TaskTemplateUpdate(BaseModel):
    id_category: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    foints_base: Optional[int] = None
    active: Optional[bool] = None


class TaskTemplateResponse(TaskTemplateBase):
    id_task_template: int

    model_config = {"from_attributes": True}