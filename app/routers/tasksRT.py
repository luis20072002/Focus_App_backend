from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import Optional
import math

from app.database import get_db
from app.models.task import Task, TaskStatus, TaskRecurrenceType, TaskNotificationType
from app.models.task_template import TaskTemplate
from app.models.foint_transaction import FointTransaction, FointReason
from app.models.user import User
from app.schemas.taskSCH import TaskCreate, TaskUpdate, TaskResponse
from dependencies import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tareas"])


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def contar_candidatas_del_dia(id_user: int, dia: date, db: Session, excluir_id: Optional[int] = None) -> int:
    """
    Cuenta cuántas tareas con is_foint_candidate=True tiene el usuario
    en un día específico. Se usa para validar el límite de 3 (RF-B06).
    excluir_id permite ignorar la tarea actual al editar.
    """
    inicio = datetime.combine(dia, datetime.min.time())
    fin = datetime.combine(dia, datetime.max.time())

    q = db.query(func.count(Task.id_task)).filter(
        Task.id_user == id_user,
        Task.is_foint_candidate == True,
        Task.scheduled_date >= inicio,
        Task.scheduled_date <= fin,
        Task.status != TaskStatus.expired,
    )
    if excluir_id:
        q = q.filter(Task.id_task != excluir_id)

    return q.scalar() or 0


def calcular_foints(foints_base: int, scheduled_date: datetime, completed_at: datetime) -> int:
    """
    Algoritmo de decremento progresivo (RF-B03):
    - Si se completa a tiempo o antes: foints_base completo.
    - Por cada hora de retraso: -10% del base.
    - Mínimo: 10% del base (redondeado hacia arriba).

    Ejemplo: base=100, 3h tarde → 100 - 30 = 70 foints.
             base=100, 12h tarde → máximo descuento → 10 foints.
    """
    if completed_at <= scheduled_date:
        return foints_base

    horas_tarde = (completed_at - scheduled_date).total_seconds() / 3600
    horas_enteras = math.floor(horas_tarde)  # Solo horas completas penalizan

    descuento = horas_enteras * 0.10  # 10% por hora
    descuento = min(descuento, 0.90)  # Máximo 90% de descuento → mínimo 10%

    foints_finales = math.ceil(foints_base * (1 - descuento))
    return max(foints_finales, math.ceil(foints_base * 0.10))


def generar_instancias_recurrentes(tarea: Task, desde: date, hasta: date) -> list[dict]:
    """
    Calcula las fechas en que una tarea recurrente aparece dentro del rango [desde, hasta].
    No crea filas en BD — solo genera representaciones virtuales para el calendario.

    Retorna lista de dicts con los datos de la tarea más la fecha de la instancia.
    """
    instancias = []
    hora = tarea.scheduled_date.time()
    fin_recurrencia = tarea.recurrence_end_date or hasta

    # Asegurar que no pasamos de la fecha de fin de recurrencia
    hasta_efectivo = min(hasta, fin_recurrencia)

    if tarea.recurrence_type == TaskRecurrenceType.daily:
        cursor = max(desde, tarea.scheduled_date.date())
        while cursor <= hasta_efectivo:
            instancias.append({
                "fecha": datetime.combine(cursor, hora),
                "tarea": tarea,
            })
            cursor += timedelta(days=1)

    elif tarea.recurrence_type in (TaskRecurrenceType.weekly, TaskRecurrenceType.custom):
        if not tarea.recurrence_days:
            return instancias
        dias_semana = {int(d.strip()) for d in tarea.recurrence_days.split(",")}
        # Python: lunes=0 ... domingo=6 / Sistema: lunes=1 ... domingo=7
        cursor = max(desde, tarea.scheduled_date.date())
        while cursor <= hasta_efectivo:
            dia_sistema = cursor.isoweekday()  # 1=lunes ... 7=domingo
            if dia_sistema in dias_semana:
                instancias.append({
                    "fecha": datetime.combine(cursor, hora),
                    "tarea": tarea,
                })
            cursor += timedelta(days=1)

    return instancias


# ---------------------------------------------------------------------------
# GET /tasks — Listar tareas del día actual (RF-F06)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TaskResponse])
def get_today_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las tareas del usuario para el día actual (según UTC).
    Incluye tareas con scheduled_date en el día de hoy, ordenadas por hora.
    Las tareas recurrentes se muestran si corresponde hoy según su configuración.

    Nota: las instancias recurrentes son virtuales — solo se devuelve la tarea
    base con su scheduled_date original. El cliente calcula si aplica hoy.
    Para una vista más precisa del calendario use GET /tasks/calendar.
    """
    hoy = datetime.utcnow().date()
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    fin_dia = datetime.combine(hoy, datetime.max.time())

    # Tareas no recurrentes del día
    tareas = db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.scheduled_date >= inicio_dia,
        Task.scheduled_date <= fin_dia,
        Task.is_recurrent == False,
    ).order_by(Task.scheduled_date).all()

    # Tareas recurrentes activas que incluyen hoy
    recurrentes = db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.is_recurrent == True,
        Task.scheduled_date <= fin_dia,  # Ya comenzaron
        and_(
            (Task.recurrence_end_date == None) |
            (Task.recurrence_end_date >= hoy)
        ),
    ).all()

    # Filtrar las recurrentes que aplican específicamente hoy
    dia_sistema = hoy.isoweekday()  # 1=lunes ... 7=domingo
    for t in recurrentes:
        aplica_hoy = False

        if t.recurrence_type == TaskRecurrenceType.daily:
            aplica_hoy = True

        elif t.recurrence_type in (TaskRecurrenceType.weekly, TaskRecurrenceType.custom):
            if t.recurrence_days:
                dias = {int(d.strip()) for d in t.recurrence_days.split(",")}
                aplica_hoy = dia_sistema in dias

        if aplica_hoy:
            tareas.append(t)

    tareas.sort(key=lambda t: t.scheduled_date)
    return tareas


# ---------------------------------------------------------------------------
# POST /tasks — Crear tarea (RF-F14, RF-F15, RF-F16)
# ---------------------------------------------------------------------------

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    datos: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Crea una nueva tarea para el usuario autenticado.

    Validaciones de negocio (RF-B06):
    - Si is_foint_candidate=True:
        · La tarea debe tener id_task_template (validado en schema).
        · La tarea NO puede ser urgente.
        · El usuario no puede tener ya 3 tareas candidatas ese día.
    - Si id_task_template viene, se verifica que exista y esté activa.
    """
    # Verificar que la plantilla existe si se envía
    if datos.id_task_template:
        plantilla = db.query(TaskTemplate).filter(
            TaskTemplate.id_task_template == datos.id_task_template,
            TaskTemplate.active == True,
        ).first()
        if not plantilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La plantilla de tarea no existe o no está activa.",
            )

    # Validaciones de candidatura a Foints
    if datos.is_foint_candidate:
        if datos.is_urgent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las tareas urgentes no pueden ser candidatas a Foints.",
            )
        dia = datos.scheduled_date.date()
        candidatas_hoy = contar_candidatas_del_dia(current_user.id_user, dia, db)
        if candidatas_hoy >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya tienes 3 tareas candidatas a Foints para ese día. Es el máximo permitido.",
            )

    nueva_tarea = Task(
        id_user=current_user.id_user,
        id_task_template=datos.id_task_template,
        is_foint_candidate=datos.is_foint_candidate,
        name=datos.name,
        description=datos.description,
        is_urgent=datos.is_urgent,
        scheduled_date=datos.scheduled_date,
        notification_type=datos.notification_type,
        status=TaskStatus.pending,
        is_recurrent=datos.is_recurrent,
        recurrence_type=datos.recurrence_type,
        recurrence_days=datos.recurrence_days,
        recurrence_end_date=datos.recurrence_end_date,
    )
    db.add(nueva_tarea)
    db.commit()
    db.refresh(nueva_tarea)
    return nueva_tarea


# ---------------------------------------------------------------------------
# PATCH /tasks/{id_task} — Editar tarea (RF-F17)
# ---------------------------------------------------------------------------

@router.patch("/{id_task}", response_model=TaskResponse)
def update_task(
    id_task: int,
    datos: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Edición parcial de una tarea del usuario autenticado.

    Restricciones (RF-F17):
    - No se puede editar una tarea ya marcada como realizada (done) o vencida (expired).
    - Si se activa is_foint_candidate:
        · La tarea (resultante) no puede ser urgente.
        · La tarea debe tener id_task_template (existente o enviado en el patch).
        · No puede superar el límite de 3 candidatas del día (excluyendo esta tarea).
    - Si se desactiva is_urgent en una tarea candidata, se permite.
    - Si se activa is_urgent en una tarea candidata, se fuerza is_foint_candidate=False.
    """
    tarea = db.query(Task).filter(
        Task.id_task == id_task,
        Task.id_user == current_user.id_user,
    ).first()

    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    if tarea.status in (TaskStatus.done, TaskStatus.expired):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede editar una tarea que ya fue realizada o venció.",
        )

    campos = datos.model_dump(exclude_unset=True)

    # Calcular estado resultante combinando BD + patch para validaciones cruzadas
    is_urgent_final = campos.get("is_urgent", tarea.is_urgent)
    is_foint_candidate_final = campos.get("is_foint_candidate", tarea.is_foint_candidate)
    id_task_template_final = campos.get("id_task_template", tarea.id_task_template)
    scheduled_date_final = campos.get("scheduled_date", tarea.scheduled_date)

    # Si se activa is_urgent y la tarea es candidata → forzar is_foint_candidate=False
    if is_urgent_final and is_foint_candidate_final:
        campos["is_foint_candidate"] = False
        is_foint_candidate_final = False

    # Verificar plantilla si se cambia
    if "id_task_template" in campos and campos["id_task_template"] is not None:
        plantilla = db.query(TaskTemplate).filter(
            TaskTemplate.id_task_template == campos["id_task_template"],
            TaskTemplate.active == True,
        ).first()
        if not plantilla:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La plantilla de tarea no existe o no está activa.",
            )

    # Validar candidatura resultante
    if is_foint_candidate_final:
        if id_task_template_final is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo las tareas de plantilla pueden ser candidatas a Foints.",
            )
        dia = scheduled_date_final.date() if isinstance(scheduled_date_final, datetime) else scheduled_date_final
        candidatas = contar_candidatas_del_dia(current_user.id_user, dia, db, excluir_id=id_task)
        if candidatas >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya tienes 3 tareas candidatas a Foints para ese día. Es el máximo permitido.",
            )

    # Aplicar cambios
    for campo, valor in campos.items():
        setattr(tarea, campo, valor)

    db.commit()
    db.refresh(tarea)
    return tarea


# ---------------------------------------------------------------------------
# DELETE /tasks/{id_task} — Eliminar tarea (RF-F17)
# ---------------------------------------------------------------------------

@router.delete("/{id_task}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    id_task: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina una tarea del usuario autenticado.

    Restricción (RF-F17): no se puede eliminar si ya fue marcada como realizada.
    Las tareas vencidas sí se pueden eliminar (el usuario puede limpiar su lista).
    Las FointTransactions asociadas se eliminan en cascada antes de borrar la tarea.
    """
    tarea = db.query(Task).filter(
        Task.id_task == id_task,
        Task.id_user == current_user.id_user,
    ).first()

    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    if tarea.status == TaskStatus.done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una tarea que ya fue realizada.",
        )

    # Eliminar transacciones de Foints asociadas antes de borrar la tarea
    db.query(FointTransaction).filter(FointTransaction.id_task == id_task).delete()

    db.delete(tarea)
    db.commit()


# ---------------------------------------------------------------------------
# POST /tasks/{id_task}/complete — Marcar como realizada (RF-F18)
# ---------------------------------------------------------------------------

@router.post("/{id_task}/complete", response_model=TaskResponse)
def complete_task(
    id_task: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marca una tarea como realizada y, si es candidata a Foints, calcula
    y acredita los puntos correspondientes.

    Lógica de Foints (RF-B02, RF-B03):
    1. Solo aplica si is_foint_candidate=True.
    2. Se obtiene foints_base de la plantilla asociada.
    3. Se aplica el algoritmo de decremento por retraso:
       - A tiempo o antes: foints_base completo.
       - Por cada hora de retraso: -10% del base.
       - Mínimo: 10% del base.
    4. Se registra FointTransaction con reason=task_completed.
    5. Se actualizan foints_season y foints_total del usuario.
    6. Se guarda foints_earned en la tarea.

    No se puede completar una tarea ya realizada o vencida.
    """
    tarea = db.query(Task).filter(
        Task.id_task == id_task,
        Task.id_user == current_user.id_user,
    ).first()

    if not tarea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada.")

    if tarea.status == TaskStatus.done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La tarea ya fue marcada como realizada.",
        )

    if tarea.status == TaskStatus.expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede completar una tarea vencida.",
        )

    ahora = datetime.utcnow()
    tarea.status = TaskStatus.done
    tarea.completed_at = ahora

    # Lógica de Foints
    if tarea.is_foint_candidate and tarea.id_task_template:
        plantilla = db.query(TaskTemplate).filter(
            TaskTemplate.id_task_template == tarea.id_task_template,
        ).first()

        if plantilla:
            foints_ganados = calcular_foints(
                foints_base=plantilla.foints_base,
                scheduled_date=tarea.scheduled_date,
                completed_at=ahora,
            )

            # Guardar en la tarea
            tarea.foints_earned = foints_ganados

            # Registrar transacción
            transaccion = FointTransaction(
                id_user=current_user.id_user,
                id_task=tarea.id_task,
                amount=foints_ganados,
                reason=FointReason.task_completed,
            )
            db.add(transaccion)

            # Actualizar contadores del usuario
            current_user.foints_season += foints_ganados
            current_user.foints_total += foints_ganados

    db.commit()
    db.refresh(tarea)
    return tarea


# ---------------------------------------------------------------------------
# GET /tasks/calendar — Vista de calendario (RF-F08, RF-F09)
# ---------------------------------------------------------------------------

@router.get("/calendar", response_model=list[TaskResponse])
def get_calendar_tasks(
    year: int = Query(..., ge=2024),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las instancias de tareas (reales y recurrentes virtuales)
    para el mes solicitado. Usado por la pantalla Calendario (RF-F08, RF-F09).

    Para tareas no recurrentes: devuelve las que caen en el mes.
    Para tareas recurrentes: genera instancias virtuales dentro del mes
    según recurrence_type, recurrence_days y recurrence_end_date.

    Las instancias recurrentes se representan con los datos de la tarea base
    pero con scheduled_date ajustado a la fecha de la instancia.

    Nota: las instancias recurrentes NO tienen id_task propio — comparten el
    de la tarea base. El cliente debe usar (id_task + fecha) como identificador
    compuesto para distinguirlas.
    """
    import calendar as cal_module

    # Rango del mes
    primer_dia = date(year, month, 1)
    ultimo_dia = date(year, month, cal_module.monthrange(year, month)[1])
    inicio_mes = datetime.combine(primer_dia, datetime.min.time())
    fin_mes = datetime.combine(ultimo_dia, datetime.max.time())

    resultados: list[Task] = []

    # 1. Tareas no recurrentes del mes
    no_recurrentes = db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.is_recurrent == False,
        Task.scheduled_date >= inicio_mes,
        Task.scheduled_date <= fin_mes,
    ).all()
    resultados.extend(no_recurrentes)

    # 2. Tareas recurrentes que podrían tener instancias en el mes
    recurrentes = db.query(Task).filter(
        Task.id_user == current_user.id_user,
        Task.is_recurrent == True,
        Task.scheduled_date <= fin_mes,  # Ya empezaron antes o durante el mes
        and_(
            (Task.recurrence_end_date == None) |
            (Task.recurrence_end_date >= primer_dia)  # No terminaron antes del mes
        ),
    ).all()

    for tarea in recurrentes:
        instancias = generar_instancias_recurrentes(tarea, primer_dia, ultimo_dia)
        for inst in instancias:
            # Crear copia virtual con la fecha de la instancia
            tarea_virtual = Task(
                id_task=tarea.id_task,
                id_user=tarea.id_user,
                id_task_template=tarea.id_task_template,
                is_foint_candidate=tarea.is_foint_candidate,
                name=tarea.name,
                description=tarea.description,
                is_urgent=tarea.is_urgent,
                scheduled_date=inst["fecha"],  # <-- fecha de la instancia
                notification_type=tarea.notification_type,
                status=tarea.status,
                foints_earned=tarea.foints_earned,
                completed_at=tarea.completed_at,
                is_recurrent=tarea.is_recurrent,
                recurrence_type=tarea.recurrence_type,
                recurrence_days=tarea.recurrence_days,
                recurrence_end_date=tarea.recurrence_end_date,
            )
            resultados.append(tarea_virtual)

    resultados.sort(key=lambda t: t.scheduled_date)
    return resultados