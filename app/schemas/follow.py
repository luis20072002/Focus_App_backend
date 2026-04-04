from pydantic import BaseModel, model_validator
from datetime import datetime


class FollowBase(BaseModel):
    id_followed: int


class FollowCreate(FollowBase):
    pass  # id_follower se obtiene del token JWT


class FollowResponse(FollowBase):
    id_follow: int
    id_follower: int
    date: datetime

    model_config = {"from_attributes": True}