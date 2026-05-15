from pydantic import BaseModel, model_validator
from typing import Optional


class BadgeBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    min_position: int
    max_position: int

    @model_validator(mode="after")
    def validate_positions(self) -> "BadgeBase":
        if self.min_position > self.max_position:
            raise ValueError("min_position no puede ser mayor que max_position")
        return self


class BadgeCreate(BadgeBase):
    pass


class BadgeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    min_position: Optional[int] = None
    max_position: Optional[int] = None


class BadgeResponse(BadgeBase):
    id_badge: int

    model_config = {"from_attributes": True}