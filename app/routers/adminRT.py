from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.badge import Badge
from app.models.user_badge import UserBadge
from app.models.ranking_cycle import RankingCycle
from app.models.ranking_history import RankingHistory
from app.models.foint_transaction import FointTransaction
from app.models.follow import Follow
from app.schemas.badgeSCH import BadgeCreate, BadgeUpdate, BadgeResponse
from app.schemas.user_badgeSCH import UserBadgeResponse
from app.schemas.userSCH import UserResponse
from dependencies import solo_admin

router = APIRouter(prefix="/admin", tags=["Panel Admin"])


# ---------------------------------------------------------------------------
# Schemas locales
# ---------------------------------------------------------------------------

class StatsResponse(BaseModel):
    """Estadísticas generales del sistema (RF-A01)."""
    usuarios_activos: int
    usuarios_baneados: int
    tareas_totales: int
    tareas_completadas: int
    tareas_completadas_hoy: int
    foints_distribuidos_total: int
    foints_distribuidos_ciclo_actual: int
    ciclo_activo: bool
    id_ciclo_activo: Optional[int] = None


class UserActivityEntry(BaseModel):
    """Entrada de actividad Foints de un usuario (RF-A02)."""
    id_task: int
    task_name: str
    scheduled_date: datetime
    completed_at: datetime
    foints_earned: int
    id_task_template: int

    model_config = {"from_attributes": False}


class UserAdminDetail(BaseModel):
    """Detalle de usuario para el panel admin."""
    id_user: int
    username: str
    name: str
    lastname: str
    email: Optional[str] = None
    phone: Optional[str] = None
    active: bool
    foints_season: int
    foints_total: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GET /admin/stats — Estadísticas generales (RF-A01)
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=StatsResponse)
def get_stats(
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Devuelve estadísticas generales del sistema para el panel admin (RF-A01):
    - Usuarios activos y baneados.
    - Total de tareas y tareas completadas (global y hoy).
    - Foints distribuidos totalmente y en el ciclo actual.
    - Estado del ciclo de ranking activo.
    """
    hoy_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    usuarios_activos = db.query(func.count(User.id_user)).filter(
        User.active == True
    ).scalar() or 0

    usuarios_baneados = db.query(func.count(User.id_user)).filter(
        User.active == False
    ).scalar() or 0

    tareas_totales = db.query(func.count(Task.id_task)).scalar() or 0

    tareas_completadas = db.query(func.count(Task.id_task)).filter(
        Task.status == TaskStatus.done
    ).scalar() or 0

    tareas_completadas_hoy = db.query(func.count(Task.id_task)).filter(
        Task.status == TaskStatus.done,
        Task.completed_at >= hoy_inicio,
    ).scalar() or 0

    foints_total = db.query(func.sum(User.foints_total)).filter(
        User.active == True
    ).scalar() or 0

    foints_ciclo = db.query(func.sum(User.foints_season)).filter(
        User.active == True
    ).scalar() or 0

    ciclo_activo = db.query(RankingCycle).filter(
        RankingCycle.closed == False
    ).first()

    return StatsResponse(
        usuarios_activos=usuarios_activos,
        usuarios_baneados=usuarios_baneados,
        tareas_totales=tareas_totales,
        tareas_completadas=tareas_completadas,
        tareas_completadas_hoy=tareas_completadas_hoy,
        foints_distribuidos_total=foints_total,
        foints_distribuidos_ciclo_actual=foints_ciclo,
        ciclo_activo=ciclo_activo is not None,
        id_ciclo_activo=ciclo_activo.id_cycle if ciclo_activo else None,
    )


# ===========================================================================
# GESTIÓN DE USUARIOS (RF-A02, RF-A03)
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /admin/users — Listar todos los usuarios (RF-A02, RF-A03)
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserAdminDetail])
def get_all_users(
    activos: Optional[bool] = Query(None, description="True=activos, False=baneados, None=todos"),
    q: Optional[str] = Query(None, description="Buscar por username, nombre o email"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Lista todos los usuarios del sistema con datos extendidos para el admin.
    Soporta filtro por estado (activos/baneados) y búsqueda por texto.
    Ordenados por fecha de registro descendente.
    """
    query = db.query(User)

    if activos is not None:
        query = query.filter(User.active == activos)

    if q:
        termino = f"%{q}%"
        query = query.filter(
            User.username.ilike(termino) |
            User.name.ilike(termino) |
            User.email.ilike(termino)
        )

    return (
        query.order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ---------------------------------------------------------------------------
# GET /admin/users/{id_user} — Detalle de usuario (RF-A02)
# ---------------------------------------------------------------------------

@router.get("/users/{id_user}", response_model=UserAdminDetail)
def get_user_detail(
    id_user: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle completo de un usuario para el panel admin (RF-A02).
    Incluye usuarios baneados.
    """
    usuario = db.query(User).filter(User.id_user == id_user).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    return usuario


# ---------------------------------------------------------------------------
# GET /admin/users/{id_user}/activity — Historial de actividad Foints (RF-A02)
# ---------------------------------------------------------------------------

@router.get("/users/{id_user}/activity", response_model=list[UserActivityEntry])
def get_user_foint_activity(
    id_user: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Historial de tareas candidatas a Foints completadas por un usuario (RF-A02).
    Permite al admin identificar patrones sospechosos de uso.

    Solo devuelve tareas con is_foint_candidate=True y status=done,
    ordenadas por completed_at descendente (más recientes primero).
    """
    usuario = db.query(User).filter(User.id_user == id_user).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    tareas = (
        db.query(Task)
        .filter(
            Task.id_user == id_user,
            Task.is_foint_candidate == True,
            Task.status == TaskStatus.done,
            Task.completed_at.isnot(None),
            Task.foints_earned.isnot(None),
            Task.id_task_template.isnot(None),
        )
        .order_by(Task.completed_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [
        UserActivityEntry(
            id_task=t.id_task,
            task_name=t.name,
            scheduled_date=t.scheduled_date,
            completed_at=t.completed_at,
            foints_earned=t.foints_earned,
            id_task_template=t.id_task_template,
        )
        for t in tareas
    ]


# ---------------------------------------------------------------------------
# POST /admin/users/{id_user}/ban — Banear usuario (RF-A03)
# ---------------------------------------------------------------------------

@router.post("/users/{id_user}/ban", response_model=UserAdminDetail)
def ban_user(
    id_user: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Desactiva la cuenta de un usuario (baneo). El usuario no podrá
    iniciar sesión ni aparecer en búsquedas (RF-A03).

    Restricciones:
    - No se puede banear a otro administrador.
    - No se puede banear a uno mismo.
    - Si ya está baneado, devuelve 400.
    """
    usuario = db.query(User).filter(User.id_user == id_user).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    if usuario.id_user == current_user.id_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes banearte a ti mismo.",
        )

    if usuario.id_role == 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se puede banear a un administrador.",
        )

    if not usuario.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya está baneado.",
        )

    usuario.active = False
    db.commit()
    db.refresh(usuario)
    return usuario


# ---------------------------------------------------------------------------
# POST /admin/users/{id_user}/unban — Desbanear usuario (RF-A03)
# ---------------------------------------------------------------------------

@router.post("/users/{id_user}/unban", response_model=UserAdminDetail)
def unban_user(
    id_user: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Reactiva la cuenta de un usuario baneado (RF-A03).
    Si ya está activo, devuelve 400.
    """
    usuario = db.query(User).filter(User.id_user == id_user).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    if usuario.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya está activo.",
        )

    usuario.active = True
    db.commit()
    db.refresh(usuario)
    return usuario


# ===========================================================================
# GESTIÓN DE BADGES (RF-A07)
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /admin/badges — Listar badges configurados (RF-A07)
# ---------------------------------------------------------------------------

@router.get("/badges", response_model=list[BadgeResponse])
def get_badges(
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Lista todos los badges configurados en el sistema, ordenados por
    min_position ascendente (top 1 primero).
    """
    return db.query(Badge).order_by(Badge.min_position.asc()).all()


# ---------------------------------------------------------------------------
# POST /admin/badges — Crear badge (RF-A07)
# ---------------------------------------------------------------------------

@router.post("/badges", response_model=BadgeResponse, status_code=status.HTTP_201_CREATED)
def create_badge(
    datos: BadgeCreate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo badge para un rango de posiciones en el ranking (RF-A07).

    Los rangos no deben solaparse entre badges — el sistema otorga el primer
    badge cuyo rango incluye la posición del usuario. Si hay solapamiento,
    el comportamiento depende del orden en que se evalúen los badges en
    rankingRT.py (primer match gana).

    Ejemplo de configuración escalonada:
      Badge "Oro":   min=1, max=1
      Badge "Plata": min=2, max=3
      Badge "Bronce": min=4, max=10
    """
    # Validar que el nombre sea único
    existente = db.query(Badge).filter(Badge.name.ilike(datos.name.strip())).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un badge con ese nombre.",
        )

    nuevo = Badge(
        name=datos.name.strip(),
        description=datos.description,
        image_url=datos.image_url,
        min_position=datos.min_position,
        max_position=datos.max_position,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


# ---------------------------------------------------------------------------
# PATCH /admin/badges/{id_badge} — Editar badge (RF-A07)
# ---------------------------------------------------------------------------

@router.patch("/badges/{id_badge}", response_model=BadgeResponse)
def update_badge(
    id_badge: int,
    datos: BadgeUpdate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Edición parcial de un badge existente (RF-A07).
    Si se cambia el nombre, valida unicidad.
    Si se cambian los rangos de posición, valida que min <= max
    considerando el estado resultante (merge de BD + payload).
    """
    badge = db.query(Badge).filter(Badge.id_badge == id_badge).first()

    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge no encontrado.",
        )

    campos = datos.model_dump(exclude_unset=True)

    if not campos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron campos para actualizar.",
        )

    # Validar unicidad del nombre si cambia
    if "name" in campos:
        nuevo_nombre = campos["name"].strip()
        existente = db.query(Badge).filter(
            Badge.name.ilike(nuevo_nombre),
            Badge.id_badge != id_badge,
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un badge con ese nombre.",
            )
        campos["name"] = nuevo_nombre

    # Validar rango resultante si solo viene uno de los dos
    min_final = campos.get("min_position", badge.min_position)
    max_final = campos.get("max_position", badge.max_position)
    if min_final > max_final:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_position no puede ser mayor que max_position.",
        )

    for campo, valor in campos.items():
        setattr(badge, campo, valor)

    db.commit()
    db.refresh(badge)
    return badge


# ---------------------------------------------------------------------------
# DELETE /admin/badges/{id_badge} — Eliminar badge (RF-A07)
# ---------------------------------------------------------------------------

@router.delete("/badges/{id_badge}", status_code=status.HTTP_204_NO_CONTENT)
def delete_badge(
    id_badge: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Elimina un badge del sistema (RF-A07).

    Restricción: no se puede eliminar si ya fue otorgado a algún usuario
    (hay registros en user_badge). Esto preserva el historial de insignias.
    """
    badge = db.query(Badge).filter(Badge.id_badge == id_badge).first()

    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge no encontrado.",
        )

    otorgado = db.query(UserBadge).filter(
        UserBadge.id_badge == id_badge
    ).first()

    if otorgado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un badge que ya fue otorgado a usuarios. "
                   "El historial de insignias debe preservarse.",
        )

    db.delete(badge)
    db.commit()


# ---------------------------------------------------------------------------
# GET /admin/badges/{id_badge}/recipients — Ver a quiénes se otorgó (RF-A07)
# ---------------------------------------------------------------------------

@router.get("/badges/{id_badge}/recipients", response_model=list[UserBadgeResponse])
def get_badge_recipients(
    id_badge: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Lista todos los usuarios que recibieron un badge específico,
    con la posición obtenida y el ciclo correspondiente (RF-A07).
    Ordenados por cycle_start_date descendente y position_obtained ascendente.
    """
    badge = db.query(Badge).filter(Badge.id_badge == id_badge).first()

    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge no encontrado.",
        )

    return (
        db.query(UserBadge)
        .filter(UserBadge.id_badge == id_badge)
        .order_by(
            UserBadge.cycle_start_date.desc(),
            UserBadge.position_obtained.asc(),
        )
        .limit(limit)
        .offset(offset)
        .all()
    )


# ---------------------------------------------------------------------------
# GET /admin/users/{id_user}/badges — Badges de un usuario (RF-A07)
# ---------------------------------------------------------------------------

@router.get("/users/{id_user}/badges", response_model=list[UserBadgeResponse])
def get_user_badges(
    id_user: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Lista todos los badges obtenidos por un usuario específico a lo largo
    de todos los ciclos (RF-A07). Ordenados por ciclo descendente.
    """
    usuario = db.query(User).filter(User.id_user == id_user).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    return (
        db.query(UserBadge)
        .filter(UserBadge.id_user == id_user)
        .order_by(UserBadge.cycle_start_date.desc())
        .all()
    )