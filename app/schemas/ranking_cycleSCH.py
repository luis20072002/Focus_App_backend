from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime


class RankingCycleBase(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_dates(self) -> "RankingCycleBase":
        if self.end_date <= self.start_date:
            raise ValueError("end_date debe ser posterior a start_date")
        return self


class RankingCycleCreate(RankingCycleBase):
    pass  # Lo crea el sistema, no el usuario


class RankingCycleUpdate(BaseModel):
    closed: Optional[bool] = None
    closed_at: Optional[datetime] = None


class RankingCycleResponse(RankingCycleBase):
    id_cycle: int
    closed: bool
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}