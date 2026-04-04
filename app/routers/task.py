from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services.auth import get_current_active_user

router= APIRouter(prefix="/tasks", tags=["Tareas"])


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    # Una tarea urgente no puede ser candidata a Foints
    if data.is_urgent and data.id_task_template is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Una tarea urgente no puede estar vinculada a una plantilla para obtener Foints"
        )

    task = Task(
        id_user=current_user.id_user,
        id_task_template=data.id_task_template,
        name=data.name,
        description=data.description,
        is_urgent=data.is_urgent,
        scheduled_date=data.scheduled_date,
        notification_type=data.notification_type,
        status=TaskStatus.pending,
        created_at=datetime.utcnow()
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=list[TaskResponse])
def get_my_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return db.query(Task).filter(Task.id_user == current_user.id_user).all()


@router.get("/today", response_model=list[TaskResponse])
def get_today_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    today = datetime.utcnow().date()
    return db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.scheduled_date >= datetime.combine(today, datetime.min.time()),
        Task.scheduled_date < datetime.combine(today, datetime.max.time())
    ).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    task = db.query(Task).filter(Task.id_task == task_id, Task.id_user == current_user.id_user).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    task = db.query(Task).filter(Task.id_task == task_id, Task.id_user == current_user.id_user).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    # No se puede editar una tarea ya realizada o con foto de confirmacion
    if task.status == TaskStatus.done:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede editar una tarea ya realizada")
    if task.confirmation_photo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede editar una tarea con foto de confirmacion enviada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    task = db.query(Task).filter(Task.id_task == task_id, Task.id_user == current_user.id_user).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    if task.status == TaskStatus.done:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar una tarea ya realizada")
    if task.confirmation_photo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar una tarea con foto de confirmacion enviada")

    db.delete(task)
    db.commit()