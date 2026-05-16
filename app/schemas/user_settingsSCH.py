from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.user_settings import ThemeType


class UserSettingsBase(BaseModel):
    notif_push: bool = True
    notif_task_reminder: bool = True
    notif_task_expired: bool = True
    notif_urgent_task: bool = True
    notif_new_follower: bool = True
    notif_suggestion_resolved: bool = True
    notif_reminder_minutes: int = 30
    theme: ThemeType = ThemeType.light
    language: str = "es"
    app_purpose: Optional[str] = None
    referred_by_friend: bool = False


class UserSettingsCreate(UserSettingsBase):
    pass  # id_user se obtiene del token JWT


class UserSettingsUpdate(BaseModel):
    notif_push: Optional[bool] = None
    notif_task_reminder: Optional[bool] = None
    notif_task_expired: Optional[bool] = None
    notif_urgent_task: Optional[bool] = None
    notif_new_follower: Optional[bool] = None
    notif_suggestion_resolved: Optional[bool] = None
    notif_reminder_minutes: Optional[int] = None
    theme: Optional[ThemeType] = None
    language: Optional[str] = None
    app_purpose: Optional[str] = None
    referred_by_friend: Optional[bool] = None


class UserSettingsResponse(UserSettingsBase):
    id_settings: int
    id_user: int
    updated_at: datetime

    model_config = {"from_attributes": True}