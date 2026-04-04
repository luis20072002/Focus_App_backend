from pydantic import BaseModel
from datetime import datetime


class LikeBase(BaseModel):
    id_photo: int


class LikeCreate(LikeBase):
    pass  # id_user se obtiene del token JWT


class LikeResponse(LikeBase):
    id_like: int
    id_user: int
    date: datetime

    model_config = {"from_attributes": True}