from pydantic import BaseModel
from datetime import date


class UserBadgeBase(BaseModel):
    id_badge: int
    cycle_start_date: date
    cycle_end_date: date
    position_obtained: int


class UserBadgeCreate(UserBadgeBase):
    id_user: int  # Lo asigna el sistema al cerrar el ciclo


class UserBadgeResponse(UserBadgeBase):
    id_user_badge: int
    id_user: int

    model_config = {"from_attributes": True}