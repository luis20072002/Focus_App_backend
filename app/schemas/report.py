from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.report import ReportStatus


class ReportBase(BaseModel):
    id_photo: int
    reason: str


class ReportCreate(ReportBase):
    pass  # id_user se obtiene del token JWT


class ReportUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    id_moderator: Optional[int] = None
    reviewed_at: Optional[datetime] = None


class ReportResponse(ReportBase):
    id_report: int
    id_user: int
    status: ReportStatus
    id_moderator: Optional[int] = None
    reported_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}