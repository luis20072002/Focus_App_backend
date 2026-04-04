from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.confirmation_photo import PhotoVisibility


class ConfirmationPhotoBase(BaseModel):
    id_task: int
    photo_url: str
    visibility: PhotoVisibility


class ConfirmationPhotoCreate(ConfirmationPhotoBase):
    pass  # id_user se obtiene del token JWT


class ConfirmationPhotoUpdate(BaseModel):
    visibility: Optional[PhotoVisibility] = None
    active: Optional[bool] = None


class ConfirmationPhotoResponse(ConfirmationPhotoBase):
    id_photo: int
    id_user: int
    uploaded_at: datetime
    active: bool

    model_config = {"from_attributes": True}