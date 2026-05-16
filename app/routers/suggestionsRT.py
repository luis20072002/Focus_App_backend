from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.template_suggestion import TemplateSuggestion, SuggestionType, SuggestionStatus
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.template_suggestionSCH import (
    TemplateSuggestionCreate,
    TemplateSuggestionUpdate,
    TemplateSuggestionResponse,
)
from app.routers.notificationsRT import notificar_usuario
from dependencies import get_current_user, solo_admin

router = APIRouter(prefix="/suggestions", tags=["Sugerencias"])


# ---------------------------------------------------------------------------
# GET /suggestions/mine — Mis sugerencias (usuario autenticado)
# ---------------------------------------------------------------------------

@router.get("/mine", response_model=list[TemplateSuggestionResponse])
def get_my_suggestions(
    status_filter: Optional[SuggestionStatus] = Query(
        None,
        alias="status",
        description="Filtrar por estado: pending, approved, rejected",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista las sugerencias enviadas por el usuario autenticado.
    Permite filtrar por estado y soporta paginación.
    Ordenadas por fecha descendente (más recientes primero).
    """
    q = db.query(TemplateSuggestion).filter(
        TemplateSuggestion.id_user == current_user.id_user,
    )

    if status_filter is not None:
        q = q.filter(TemplateSuggestion.status == status_filter)

    return (
        q.order_by(TemplateSuggestion.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


# ---------------------------------------------------------------------------
# POST /suggestions — Enviar sugerencia (RF-B08)
# ---------------------------------------------------------------------------

@router.post("", response_model=TemplateSuggestionResponse, status_code=status.HTTP_201_CREATED)
def create_suggestion(
    datos: TemplateSuggestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    El usuario autenticado envía una sugerencia de nueva tarea de plantilla
    o nueva categoría (RF-B08).

    Validación: el usuario no puede tener más de 3 sugerencias pendientes
    simultáneamente — evita spam y garantiza que el admin pueda gestionarlas.

    La sugerencia se crea con status=pending y date=ahora.
    No se notifica al admin aquí — el panel admin lista las pendientes.
    """
    # Límite de sugerencias pendientes por usuario
    pendientes = db.query(TemplateSuggestion).filter(
        TemplateSuggestion.id_user == current_user.id_user,
        TemplateSuggestion.status == SuggestionStatus.pending,
    ).count()

    if pendientes >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tienes 3 sugerencias pendientes de revisión. "
                   "Espera a que sean revisadas antes de enviar más.",
        )

    nueva = TemplateSuggestion(
        id_user=current_user.id_user,
        type=datos.type,
        content=datos.content.strip(),
        status=SuggestionStatus.pending,
        id_admin=None,
        date=datetime.utcnow(),
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


# ---------------------------------------------------------------------------
# DELETE /suggestions/{id_suggestion} — Eliminar sugerencia propia
# ---------------------------------------------------------------------------

@router.delete("/{id_suggestion}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_suggestion(
    id_suggestion: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    El usuario autenticado elimina una de sus propias sugerencias.

    Restricción: solo se pueden eliminar sugerencias en estado pending.
    Una sugerencia ya revisada (approved/rejected) no se puede eliminar
    — forma parte del historial de revisiones del admin.
    """
    sugerencia = db.query(TemplateSuggestion).filter(
        TemplateSuggestion.id_suggestion == id_suggestion,
        TemplateSuggestion.id_user == current_user.id_user,
    ).first()

    if not sugerencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugerencia no encontrada.",
        )

    if sugerencia.status != SuggestionStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes eliminar sugerencias que aún estén pendientes de revisión.",
        )

    db.delete(sugerencia)
    db.commit()


# ===========================================================================
# ENDPOINTS EXCLUSIVOS DE ADMIN (RF-A04)
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /suggestions — Listar todas las sugerencias (solo admin, RF-A04)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TemplateSuggestionResponse])
def get_all_suggestions(
    status_filter: Optional[SuggestionStatus] = Query(
        None,
        alias="status",
        description="Filtrar por estado. Sin filtro devuelve todas.",
    ),
    type_filter: Optional[SuggestionType] = Query(
        None,
        alias="type",
        description="Filtrar por tipo: task, category.",
    ),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Lista todas las sugerencias de todos los usuarios.
    Solo accesible por administradores (RF-A04).

    Filtros disponibles:
    - ?status=pending   → pendientes de revisión (vista principal del admin)
    - ?status=approved  → aprobadas
    - ?status=rejected  → rechazadas
    - ?type=task        → sugerencias de nuevas tareas de plantilla
    - ?type=category    → sugerencias de nuevas categorías

    Ordenadas: primero las pendientes, luego por fecha descendente.
    """
    q = db.query(TemplateSuggestion)

    if status_filter is not None:
        q = q.filter(TemplateSuggestion.status == status_filter)

    if type_filter is not None:
        q = q.filter(TemplateSuggestion.type == type_filter)

    return (
        q.order_by(
            # Pendientes primero, luego el resto por fecha
            TemplateSuggestion.status.asc(),   # 'aprobada' < 'pendiente' < 'rechazada' alfabéticamente
            TemplateSuggestion.date.desc(),
        )
        .limit(limit)
        .offset(offset)
        .all()
    )


# ---------------------------------------------------------------------------
# GET /suggestions/{id_suggestion} — Ver detalle de sugerencia (solo admin)
# ---------------------------------------------------------------------------

@router.get("/{id_suggestion}", response_model=TemplateSuggestionResponse)
def get_suggestion(
    id_suggestion: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Devuelve el detalle de una sugerencia específica.
    Solo accesible por administradores (RF-A04).
    """
    sugerencia = db.query(TemplateSuggestion).filter(
        TemplateSuggestion.id_suggestion == id_suggestion,
    ).first()

    if not sugerencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugerencia no encontrada.",
        )

    return sugerencia


# ---------------------------------------------------------------------------
# PATCH /suggestions/{id_suggestion}/review — Revisar sugerencia (solo admin, RF-A04)
# ---------------------------------------------------------------------------

@router.patch("/{id_suggestion}/review", response_model=TemplateSuggestionResponse)
def review_suggestion(
    id_suggestion: int,
    datos: TemplateSuggestionUpdate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    El administrador aprueba o rechaza una sugerencia (RF-A04).

    Reglas:
    - Solo se pueden revisar sugerencias en estado pending.
      Una sugerencia ya revisada no se puede cambiar de estado.
    - Al revisar, se registra id_admin = admin que la revisó.
    - Se notifica al usuario que envió la sugerencia (RF-F22):
        · Si aprobada: notificación tipo suggestion_resolved con mensaje positivo.
        · Si rechazada: notificación tipo suggestion_resolved con mensaje neutro.

    El nuevo status debe ser approved o rejected — no se puede volver a pending.
    """
    if datos.status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar el nuevo estado: approved o rejected.",
        )

    if datos.status == SuggestionStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes cambiar el estado a pending. Solo approved o rejected.",
        )

    sugerencia = db.query(TemplateSuggestion).filter(
        TemplateSuggestion.id_suggestion == id_suggestion,
    ).first()

    if not sugerencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sugerencia no encontrada.",
        )

    if sugerencia.status != SuggestionStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta sugerencia ya fue revisada (estado actual: {sugerencia.status.value}). "
                   "No se puede modificar una decisión tomada.",
        )

    # Aplicar revisión
    sugerencia.status = datos.status
    sugerencia.id_admin = current_user.id_user
    db.commit()
    db.refresh(sugerencia)

    # Notificar al usuario que envió la sugerencia (RF-F22)
    tipo_sugerencia = sugerencia.type.value  # "tarea" o "categoria"

    if datos.status == SuggestionStatus.approved:
        mensaje = (
            f"Tu sugerencia de {tipo_sugerencia} fue aprobada. "
            "¡Gracias por contribuir a Focus App!"
        )
        titulo_push = "Sugerencia aprobada"
    else:
        mensaje = (
            f"Tu sugerencia de {tipo_sugerencia} no fue aprobada esta vez. "
            "Puedes enviar nuevas sugerencias cuando quieras."
        )
        titulo_push = "Sugerencia revisada"

    notificar_usuario(
        id_user=sugerencia.id_user,
        tipo=NotificationType.suggestion_resolved,
        mensaje=mensaje,
        titulo_push=titulo_push,
        db=db,
        id_reference=sugerencia.id_suggestion,
    )

    return sugerencia