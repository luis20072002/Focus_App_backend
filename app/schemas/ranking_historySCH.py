from pydantic import BaseModel, field_validator
from datetime import date


class RankingHistoryBase(BaseModel):
    global_position: int
    foints_cycle: int

    @field_validator("global_position")
    @classmethod
    def position_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("global_position debe ser mayor que 0")
        return v

    @field_validator("foints_cycle")
    @classmethod
    def foints_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("foints_cycle no puede ser negativo")
        return v


class RankingHistoryCreate(RankingHistoryBase):
    id_user: int  # Lo asigna el sistema al cerrar el ciclo


class RankingHistoryResponse(RankingHistoryBase):
    id_history: int
    id_user: int

    model_config = {"from_attributes": True}