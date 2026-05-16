from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.follow import Follow
from app.models.badge import Badge
from app.models.user_badge import UserBadge
from app.models.ranking_cycle import RankingCycle
from app.models.ranking_history import RankingHistory
from app.schemas.ranking_cycleSCH import RankingCycleCreate, RankingCycleResponse
from app.schemas.ranking_historySCH import RankingHistoryResponse
from dependencies import get_current_user, solo_admin

router = APIRouter(prefix="/ranking", tags=["Ranking"])


# ---------------------------------------------------------------------------
# Schemas locales
# ---------------------------------------------------------------------------

class RankingEntry(BaseModel):
    """Entrada del ranking con datos del usuario y su posición."""
    position: int
    id_user: int
    username: str
    name: str
    lastname: str
    profile_picture: Optional[str] = None
    foints_season: int

    model_config = {"from_attributes": False}


class CycleCloseResponse(BaseModel):
    """Respuesta al cerrar un ciclo."""
    message: str
    id_cycle: int
    total_usuarios_rankeados: int
    badges_otorgados: int


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def get_ciclo_activo(db: Session) -> Optional[RankingCycle]:
    """Devuelve el ciclo abierto actual, o None si no hay ninguno."""
    return db.query(RankingCycle).filter(
        RankingCycle.closed == False,
    ).first()


def otorgar_badges(
    usuarios_ordenados: list[User],
    ciclo: RankingCycle,
    db: Session,
) -> int:
    """
    Otorga insignias a los usuarios del top según los rangos definidos
    en la tabla Badge (min_position, max_position).

    Retorna el número de badges otorgados.
    """
    badges = db.query(Badge).all()
    if not badges:
        return 0

    cycle_start = ciclo.start_date.date()
    cycle_end = ciclo.end_date.date()

    badges_otorgados = 0

    for posicion, usuario in enumerate(usuarios_ordenados, start=1):
        # Buscar el badge que cubre esta posición
        badge_aplicable = next(
            (b for b in badges if b.min_position <= posicion <= b.max_position),
            None,
        )

        if badge_aplicable is None:
            # No hay badge definido para posiciones más allá del top configurado
            break

        # Verificar que no se haya otorgado ya este badge en este ciclo
        ya_tiene = db.query(UserBadge).filter(
            UserBadge.id_user == usuario.id_user,
            UserBadge.id_badge == badge_aplicable.id_badge,
            UserBadge.cycle_start_date == cycle_start,
        ).first()

        if ya_tiene:
            continue

        nuevo_badge = UserBadge(
            id_user=usuario.id_user,
            id_badge=badge_aplicable.id_badge,
            cycle_start_date=cycle_start,
            cycle_end_date=cycle_end,
            position_obtained=posicion,
        )
        db.add(nuevo_badge)
        badges_otorgados += 1

    return badges_otorgados


# ---------------------------------------------------------------------------
# GET /ranking/global — Ranking global por foints_season (RF-B04)
# ---------------------------------------------------------------------------

@router.get("/global", response_model=list[RankingEntry])
def get_global_ranking(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve el ranking global de usuarios ordenado por foints_season descendente.

    La posición se calcula en memoria sobre los usuarios activos con foints > 0,
    aplicando paginación después. Esto garantiza que la posición reflejada sea
    la posición real global, no relativa a la página.

    Usuarios con foints_season = 0 no aparecen en el ranking — aún no han
    completado ninguna tarea candidata en el ciclo actual.

    La posición del usuario autenticado en el ranking global se puede obtener
    de este mismo endpoint buscando su id_user en los resultados, o usando
    GET /ranking/me.
    """
    usuarios = (
        db.query(User)
        .filter(
            User.active == True,
            User.foints_season > 0,
        )
        .order_by(User.foints_season.desc(), User.username.asc())
        .all()
    )

    # Asignar posiciones reales (1-based) antes de paginar
    resultado = []
    for posicion, usuario in enumerate(usuarios, start=1):
        resultado.append(RankingEntry(
            position=posicion,
            id_user=usuario.id_user,
            username=usuario.username,
            name=usuario.name,
            lastname=usuario.lastname,
            profile_picture=usuario.profile_picture,
            foints_season=usuario.foints_season,
        ))

    # Aplicar paginación después de asignar posiciones
    return resultado[offset: offset + limit]


# ---------------------------------------------------------------------------
# GET /ranking/friends — Ranking entre amigos (RF-B04)
# ---------------------------------------------------------------------------

@router.get("/friends", response_model=list[RankingEntry])
def get_friends_ranking(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve el ranking entre amigos del usuario autenticado.
    Los amigos son usuarios con seguimiento mutuo (Follow bidireccional).

    Incluye al propio usuario autenticado en el ranking para que pueda
    ver su posición relativa frente a sus amigos.

    No aplica paginación — el número de amigos rara vez justifica paginar
    y la app espera la lista completa para renderizar el widget de ranking.
    """
    # Subquery: IDs de usuarios que yo sigo
    yo_sigo = db.query(Follow.id_followed).filter(
        Follow.id_follower == current_user.id_user,
    ).subquery()

    # Subquery: IDs de usuarios que me siguen
    me_siguen = db.query(Follow.id_follower).filter(
        Follow.id_followed == current_user.id_user,
    ).subquery()

    # Amigos = intersección (seguimiento mutuo)
    amigos = (
        db.query(User)
        .filter(
            User.id_user.in_(yo_sigo),
            User.id_user.in_(me_siguen),
            User.active == True,
        )
        .all()
    )

    # Incluir al usuario autenticado
    participantes = amigos + [current_user]

    # Eliminar duplicados (por si current_user aparece en amigos por algún edge case)
    vistos = set()
    unicos = []
    for u in participantes:
        if u.id_user not in vistos:
            vistos.add(u.id_user)
            unicos.append(u)

    # Ordenar por foints_season desc, username asc como desempate
    unicos.sort(key=lambda u: (-u.foints_season, u.username))

    resultado = []
    for posicion, usuario in enumerate(unicos, start=1):
        resultado.append(RankingEntry(
            position=posicion,
            id_user=usuario.id_user,
            username=usuario.username,
            name=usuario.name,
            lastname=usuario.lastname,
            profile_picture=usuario.profile_picture,
            foints_season=usuario.foints_season,
        ))

    return resultado


# ---------------------------------------------------------------------------
# GET /ranking/me — Mi posición en el ranking global (RF-F07)
# ---------------------------------------------------------------------------

@router.get("/me", response_model=RankingEntry)
def get_my_ranking_position(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve la posición global del usuario autenticado en el ciclo actual.

    La posición se calcula contando cuántos usuarios activos tienen más
    foints_season que el usuario actual (más eficiente que cargar toda la lista).

    Si el usuario tiene foints_season = 0, retorna 404 indicando que aún
    no tiene posición en el ranking del ciclo actual.
    """
    if current_user.foints_season == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no tienes posición en el ranking. Completa tareas candidatas para aparecer.",
        )

    # Contar usuarios con más foints que yo (todos activos con foints > 0)
    usuarios_por_encima = db.query(func.count(User.id_user)).filter(
        User.active == True,
        User.foints_season > current_user.foints_season,
    ).scalar() or 0

    posicion = usuarios_por_encima + 1

    return RankingEntry(
        position=posicion,
        id_user=current_user.id_user,
        username=current_user.username,
        name=current_user.name,
        lastname=current_user.lastname,
        profile_picture=current_user.profile_picture,
        foints_season=current_user.foints_season,
    )


# ---------------------------------------------------------------------------
# GET /ranking/history — Historial de rankings por ciclo (RF-A06)
# ---------------------------------------------------------------------------

@router.get("/history", response_model=list[RankingHistoryResponse])
def get_ranking_history(
    id_cycle: Optional[int] = Query(None, description="Filtrar por ciclo específico"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve el historial de posiciones de ciclos cerrados.
    Soporta filtro por ciclo específico y paginación.

    Accesible por cualquier usuario autenticado — permite ver el historial
    de rankings pasados. El panel admin usa este endpoint con id_cycle
    para ver el snapshot completo de un ciclo cerrado (RF-A06).
    """
    q = db.query(RankingHistory)

    if id_cycle is not None:
        # Verificar que el ciclo existe
        ciclo = db.query(RankingCycle).filter(
            RankingCycle.id_cycle == id_cycle,
        ).first()
        if not ciclo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ciclo no encontrado.",
            )
        q = q.filter(RankingHistory.id_cycle == id_cycle)

    return (
        q.order_by(RankingHistory.id_cycle.desc(), RankingHistory.global_position.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ---------------------------------------------------------------------------
# GET /ranking/cycles — Listar ciclos (RF-A06)
# ---------------------------------------------------------------------------

@router.get("/cycles", response_model=list[RankingCycleResponse])
def get_cycles(
    solo_cerrados: bool = Query(False, description="Si True, devuelve solo los ciclos cerrados"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista todos los ciclos de ranking registrados.
    Con ?solo_cerrados=true devuelve solo los ciclos ya cerrados.
    Accesible por cualquier usuario autenticado.
    """
    q = db.query(RankingCycle)

    if solo_cerrados:
        q = q.filter(RankingCycle.closed == True)

    return q.order_by(RankingCycle.start_date.desc()).all()


# ---------------------------------------------------------------------------
# GET /ranking/cycles/active — Ciclo activo actual
# ---------------------------------------------------------------------------

@router.get("/cycles/active", response_model=RankingCycleResponse)
def get_active_cycle(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve el ciclo de ranking actualmente abierto.
    Retorna 404 si no hay ningún ciclo activo.
    """
    ciclo = get_ciclo_activo(db)

    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay un ciclo de ranking activo en este momento.",
        )

    return ciclo


# ===========================================================================
# ENDPOINTS EXCLUSIVOS DE ADMIN
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /ranking/cycles — Crear nuevo ciclo (solo admin, RF-B05)
# ---------------------------------------------------------------------------

@router.post("/cycles", response_model=RankingCycleResponse, status_code=status.HTTP_201_CREATED)
def create_cycle(
    datos: RankingCycleCreate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo ciclo de ranking.
    Solo accesible por administradores (RF-B05).

    Restricción: no puede haber dos ciclos abiertos simultáneamente.
    Si ya hay un ciclo activo, se debe cerrar primero con POST /ranking/cycles/close.

    El sistema está diseñado para ciclos de ~15 días (RF-B05), pero el admin
    define libremente start_date y end_date.
    """
    # No puede haber dos ciclos abiertos a la vez
    ciclo_activo = get_ciclo_activo(db)
    if ciclo_activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un ciclo activo (id={ciclo_activo.id_cycle}). "
                   "Ciérralo antes de crear uno nuevo con POST /ranking/cycles/close.",
        )

    nuevo_ciclo = RankingCycle(
        start_date=datos.start_date,
        end_date=datos.end_date,
        closed=False,
        closed_at=None,
    )
    db.add(nuevo_ciclo)
    db.commit()
    db.refresh(nuevo_ciclo)
    return nuevo_ciclo


# ---------------------------------------------------------------------------
# POST /ranking/cycles/close — Cerrar ciclo activo (solo admin, RF-B05)
# ---------------------------------------------------------------------------

@router.post("/cycles/close", response_model=CycleCloseResponse)
def close_active_cycle(
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Cierra el ciclo de ranking activo. Proceso completo (RF-B05):

    1. Verifica que existe un ciclo abierto.
    2. Obtiene todos los usuarios activos con foints_season > 0,
       ordenados por foints_season desc (ranking final del ciclo).
    3. Guarda un snapshot en RankingHistory con la posición global y
       foints_cycle de cada usuario.
    4. Otorga badges a los usuarios del top según los rangos definidos
       en la tabla Badge (min_position, max_position).
    5. Resetea foints_season a 0 en todos los usuarios activos.
    6. Marca el ciclo como closed=True con closed_at=ahora.

    Todo ocurre en una sola transacción — si algo falla, nada se guarda.
    Solo accesible por administradores.
    """
    ciclo = get_ciclo_activo(db)

    if not ciclo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay un ciclo de ranking activo para cerrar.",
        )

    ahora = datetime.utcnow()

    # 1. Obtener ranking final: usuarios activos con foints > 0, ordenados
    usuarios_rankeados = (
        db.query(User)
        .filter(
            User.active == True,
            User.foints_season > 0,
        )
        .order_by(User.foints_season.desc(), User.username.asc())
        .all()
    )

    # 2. Guardar snapshot en RankingHistory
    for posicion, usuario in enumerate(usuarios_rankeados, start=1):
        entrada = RankingHistory(
            id_user=usuario.id_user,
            global_position=posicion,
            foints_cycle=usuario.foints_season,
            id_cycle=ciclo.id_cycle,
        )
        db.add(entrada)

    # 3. Otorgar badges según posición (antes del flush para tener los IDs)
    db.flush()  # Para que los RankingHistory tengan id_history sin hacer commit aún
    badges_otorgados = otorgar_badges(usuarios_rankeados, ciclo, db)

    # 4. Resetear foints_season de TODOS los usuarios activos a 0
    db.query(User).filter(User.active == True).update({"foints_season": 0})

    # 5. Cerrar el ciclo
    ciclo.closed = True
    ciclo.closed_at = ahora

    db.commit()

    return CycleCloseResponse(
        message=f"Ciclo {ciclo.id_cycle} cerrado correctamente.",
        id_cycle=ciclo.id_cycle,
        total_usuarios_rankeados=len(usuarios_rankeados),
        badges_otorgados=badges_otorgados,
    )