from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from dependencies import get_current_user, solo_moderador_o_admin

router = APIRouter(prefix="/tasks", tags=["Tareas"])


@router.get("/", response_model=list[TaskResponse])
def get_mis_tareas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Task).filter(Task.id_user == current_user.id_user).all()


@router.get("/today", response_model=list[TaskResponse])
def get_tareas_hoy(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    return db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.scheduled_date >= datetime.combine(today, datetime.min.time()),
        Task.scheduled_date < datetime.combine(today, datetime.max.time())
    ).all()


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

    tarea = Task(
        id_user=current_user.id_user,
        id_task_template=datos.id_task_template,
        name=datos.name,
        description=datos.description,
        is_urgent=datos.is_urgent,
        scheduled_date=datos.scheduled_date,
        notification_type=datos.notification_type,
        status=TaskStatus.pending,
        created_at=datetime.utcnow()
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