from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.models.task import TaskNotificationType, TaskStatus


class TaskBase(BaseModel):
    id_task_template: Optional[int] = None
    name: str
    description: Optional[str] = None
    is_urgent: bool = False
    scheduled_date: datetime
    notification_type: TaskNotificationType
    status: TaskStatus = TaskStatus.pending


class TaskCreate(TaskBase):
    pass  # id_user se obtiene del token JWT, no del body


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_urgent: Optional[bool] = None
    scheduled_date: Optional[datetime] = None
    notification_type: Optional[TaskNotificationType] = None
    status: Optional[TaskStatus] = None


class TaskResponse(TaskBase):
    id_task: int
    id_user: int
    foints_earned: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}