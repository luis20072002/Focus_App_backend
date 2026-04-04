from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.notification import NotificationType


class NotificationBase(BaseModel):
    type: NotificationType
    message: str
    id_reference: Optional[int] = None


class NotificationCreate(NotificationBase):
    id_user: int  # Lo asigna el sistema internamente, no el usuario


class NotificationUpdate(BaseModel):
    read: Optional[bool] = None


class NotificationResponse(NotificationBase):
    id_notification: int
    id_user: int
    read: bool
    date: datetime

    model_config = {"from_attributes": True}