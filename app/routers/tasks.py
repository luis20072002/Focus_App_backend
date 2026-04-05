from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.database import get_db
from app.models.task import Task, TaskStatus, TaskRecurrenceType
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from dependencies import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tareas"])


def tarea_aplica_hoy(tarea: Task, hoy: date) -> bool:
    """
    Determina si una tarea recurrente aplica para el dia dado.
    hoy: date con la fecha a evaluar
    Retorna True si la tarea debe aparecer ese dia.
    """
    # Si ya paso la fecha de fin de recurrencia no aplica
    if tarea.recurrence_end_date and hoy > tarea.recurrence_end_date:
        return False

    # La tarea no puede aparecer antes de su fecha de inicio
    if hoy < tarea.scheduled_date.date():
        return False

    if tarea.recurrence_type == TaskRecurrenceType.daily:
        return True

    if tarea.recurrence_type in (TaskRecurrenceType.weekly, TaskRecurrenceType.custom):
        if not tarea.recurrence_days:
            return False
        # isoweekday(): lunes=1 ... domingo=7
        dia_hoy = str(hoy.isoweekday())
        dias = [d.strip() for d in tarea.recurrence_days.split(",")]
        return dia_hoy in dias

    return False


@router.get("/", response_model=list[TaskResponse])
def get_mis_tareas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Task).filter(Task.id_user == current_user.id_user).all()


@router.get("/today", response_model=list[TaskResponse])
def get_tareas_hoy(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    hoy = datetime.utcnow().date()
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    fin_dia = datetime.combine(hoy, datetime.max.time())

    # Tareas normales programadas para hoy
    tareas_normales = db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.is_recurrent == False,
        Task.scheduled_date >= inicio_dia,
        Task.scheduled_date <= fin_dia
    ).all()

    # Tareas recurrentes que aplican para hoy
    tareas_recurrentes = db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.is_recurrent == True
    ).all()

    recurrentes_hoy = [t for t in tareas_recurrentes if tarea_aplica_hoy(t, hoy)]

    return tareas_normales + recurrentes_hoy


@router.get("/{task_id}", response_model=TaskResponse)
def get_tarea(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tarea = db.query(Task).filter(Task.id_task == task_id, Task.id_user == current_user.id_user).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea


@router.post("/", response_model=TaskResponse, status_code=201)
def crear_tarea(datos: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if datos.is_urgent and datos.id_task_template is not None:
        raise HTTPException(
            status_code=400,
            detail="Una tarea urgente no puede estar vinculada a una plantilla para obtener Foints"
        )

    if datos.is_urgent and datos.is_recurrent:
        raise HTTPException(
            status_code=400,
            detail="Una tarea urgente no puede ser recurrente"
        )

    tarea = Task(
        id_user=current_user.id_user,
        id_task_template=datos.id_task_template,
        name=datos.name,
        description=datos.description,
        is_urgent=datos.is_urgent,
        scheduled_date=datos.scheduled_date,
        notification_type=datos.notification_type,
        status=TaskStatus.pending,
        created_at=datetime.utcnow(),
        is_recurrent=datos.is_recurrent,
        recurrence_type=datos.recurrence_type,
        recurrence_days=datos.recurrence_days,
        recurrence_end_date=datos.recurrence_end_date
    )
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    return tarea


@router.put("/{task_id}", response_model=TaskResponse)
def actualizar_tarea(
    task_id: int,
    datos: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tarea = db.query(Task).filter(Task.id_task == task_id, Task.id_user == current_user.id_user).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if tarea.status == TaskStatus.done:
        raise HTTPException(status_code=400, detail="No se puede editar una tarea ya realizada")
    if tarea.confirmation_photo:
        raise HTTPException(status_code=400, detail="No se puede editar una tarea con foto de confirmacion enviada")

    if datos.name is not None:
        tarea.name = datos.name
    if datos.description is not None:
        tarea.description = datos.description
    if datos.is_urgent is not None:
        tarea.is_urgent = datos.is_urgent
    if datos.scheduled_date is not None:
        tarea.scheduled_date = datos.scheduled_date
    if datos.notification_type is not None:
        tarea.notification_type = datos.notification_type
    if datos.status is not None:
        tarea.status = datos.status
    if datos.is_recurrent is not None:
        tarea.is_recurrent = datos.is_recurrent
    if datos.recurrence_type is not None:
        tarea.recurrence_type = datos.recurrence_type
    if datos.recurrence_days is not None:
        tarea.recurrence_days = datos.recurrence_days
    if datos.recurrence_end_date is not None:
        tarea.recurrence_end_date = datos.recurrence_end_date

    db.commit()
    db.refresh(tarea)
    return tarea


@router.delete("/{task_id}", status_code=200)
def eliminar_tarea(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tarea = db.query(Task).filter(Task.id_task == task_id, Task.id_user == current_user.id_user).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if tarea.status == TaskStatus.done:
        raise HTTPException(status_code=400, detail="No se puede eliminar una tarea ya realizada")
    if tarea.confirmation_photo:
        raise HTTPException(status_code=400, detail="No se puede eliminar una tarea con foto de confirmacion enviada")

    db.delete(tarea)
    db.commit()
    return {"detail": "Tarea eliminada correctamente"}