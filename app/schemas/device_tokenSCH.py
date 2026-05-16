from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.device_token import DevicePlatform


class DeviceTokenBase(BaseModel):
    token: str
    platform: DevicePlatform


class DeviceTokenCreate(DeviceTokenBase):
    pass  # id_user se obtiene del token JWT


class DeviceTokenResponse(DeviceTokenBase):
    id_device: int
    id_user: int
    created_at: datetime

    model_config = {"from_attributes": True}