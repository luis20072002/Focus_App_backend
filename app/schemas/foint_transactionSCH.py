from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.models.foint_transaction import FointReason


class FointTransactionBase(BaseModel):
    id_task: Optional[int] = None
    amount: int
    reason: FointReason

    @field_validator("amount")
    @classmethod
    def amount_not_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("amount no puede ser 0")
        return v


class FointTransactionCreate(FointTransactionBase):
    id_user: int  # Lo asigna el sistema internamente


class FointTransactionResponse(FointTransactionBase):
    id_transaction: int
    id_user: int
    created_at: datetime

    model_config = {"from_attributes": True}