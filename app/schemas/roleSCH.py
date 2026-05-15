from pydantic import BaseModel
from typing import Optional


class RoleBase(BaseModel):
    name_role: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    id_role: int  # No es autoincremental en el modelo, se asigna manualmente


class RoleUpdate(BaseModel):
    name_role: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id_role: int

    model_config = {"from_attributes": True}