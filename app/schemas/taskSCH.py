from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime, date
from app.models.task import (
    TaskNotificationType,
    TaskStatus,
    TaskRecurrenceType
)


class TaskBase(BaseModel):
    id_task_template: Optional[int] = None
    is_foint_candidate: bool = False
    name: str
    description: Optional[str] = None
    is_urgent: bool = False
    scheduled_date: datetime
    notification_type: TaskNotificationType
    status: TaskStatus = TaskStatus.pending

    # Recurrencia
    is_recurrent: bool = False
    recurrence_type: TaskRecurrenceType = TaskRecurrenceType.none
    recurrence_days: Optional[str] = None  # "1,2,3" = lunes, martes, miercoles
    recurrence_end_date: Optional[date] = None

    @model_validator(mode="after")
    def validar_foints(self) -> "TaskBase":
        if self.is_foint_candidate and self.id_task_template is None:
            raise ValueError("Solo las tareas de plantilla pueden ser candidatas a Foints")
        return self

    @model_validator(mode="after")
    def validar_recurrencia(self) -> "TaskBase":
        if self.is_recurrent:
            if self.recurrence_type == TaskRecurrenceType.none:
                raise ValueError("Si la tarea es recurrente debe especificar el tipo de recurrencia")
            if self.recurrence_type in (TaskRecurrenceType.weekly, TaskRecurrenceType.custom):
                if not self.recurrence_days:
                    raise ValueError("Debe especificar los dias de recurrencia para recurrencia semanal o personalizada")
                dias = self.recurrence_days.split(",")
                for dia in dias:
                    if not dia.strip().isdigit() or int(dia.strip()) not in range(1, 8):
                        raise ValueError("Los dias de recurrencia deben ser numeros del 1 (lunes) al 7 (domingo)")
        else:
            self.recurrence_type = TaskRecurrenceType.none
            self.recurrence_days = None
            self.recurrence_end_date = None
        return self


class TaskCreate(TaskBase):
    pass  # id_user se obtiene del token JWT


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_urgent: Optional[bool] = None
    scheduled_date: Optional[datetime] = None
    notification_type: Optional[TaskNotificationType] = None
    status: Optional[TaskStatus] = None

    id_task_template: Optional[int] = None
    is_foint_candidate: Optional[bool] = None

    is_recurrent: Optional[bool] = None
    recurrence_type: Optional[TaskRecurrenceType] = None
    recurrence_days: Optional[str] = None
    recurrence_end_date: Optional[date] = None

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_urgent: Optional[bool] = None
    scheduled_date: Optional[datetime] = None
    notification_type: Optional[TaskNotificationType] = None
    status: Optional[TaskStatus] = None
    id_task_template: Optional[int] = None
    is_foint_candidate: Optional[bool] = None
    is_recurrent: Optional[bool] = None
    recurrence_type: Optional[TaskRecurrenceType] = None
    recurrence_days: Optional[str] = None
    recurrence_end_date: Optional[date] = None

    @model_validator(mode="after")
    def validar_patch_basico(self):
        # Si se apaga la recurrencia explícitamente, limpiar campos relacionados
        if self.is_recurrent is False:
            self.recurrence_type = TaskRecurrenceType.none
            self.recurrence_days = None
            self.recurrence_end_date = None

        # Si viene recurrence_type semanal/personalizado con days, validar formato
        if self.recurrence_type in (TaskRecurrenceType.weekly, TaskRecurrenceType.custom):
            if self.recurrence_days is not None:
                dias = self.recurrence_days.split(",")
                for dia in dias:
                    if not dia.strip().isdigit() or int(dia.strip()) not in range(1, 8):
                        raise ValueError(
                            "Los dias de recurrencia deben ser numeros del 1 (lunes) al 7 (domingo)"
                        )

        # Nota: las validaciones cruzadas con el estado actual en BD
        # (is_foint_candidate vs id_task_template existente, límite de 3 candidatas,
        # is_recurrent vs recurrence_type existente) deben hacerse en el endpoint
        # haciendo merge del estado actual con el payload antes de aplicar cambios.
        return self

class TaskResponse(TaskBase):
    id_task: int
    id_user: int
    foints_earned: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}