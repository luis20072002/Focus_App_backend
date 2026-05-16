from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.user_settings import UserSettings
from app.models.user import User
from app.schemas.user_settingsSCH import UserSettingsUpdate, UserSettingsResponse
from dependencies import get_current_user

router = APIRouter(prefix="/settings", tags=["Configuracion"])


# ---------------------------------------------------------------------------
# GET /settings — Ver mi configuración (RF-F23, RF-F25)
# ---------------------------------------------------------------------------

@router.get("", response_model=UserSettingsResponse)
def get_my_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve la configuración del usuario autenticado.
    El registro de UserSettings se crea automáticamente al registrar el usuario,
    por lo que siempre debe existir. Si no existe (datos inconsistentes), devuelve 404.
    """
    configuracion = db.query(UserSettings).filter(
        UserSettings.id_user == current_user.id_user,
    ).first()

    if not configuracion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada. Contacta al soporte.",
        )

    return configuracion


# ---------------------------------------------------------------------------
# PATCH /settings — Actualizar mi configuración (RF-F23, RF-F25)
# ---------------------------------------------------------------------------

@router.patch("", response_model=UserSettingsResponse)
def update_my_settings(
    datos: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Edición parcial de la configuración del usuario autenticado.

    Campos editables:
    - notif_push: activa/desactiva todas las notificaciones push.
    - notif_task_reminder: recordatorio antes de una tarea.
    - notif_task_expired: aviso de tarea vencida.
    - notif_urgent_task: aviso de tarea urgente.
    - notif_new_follower: aviso de nuevo seguidor.
    - notif_suggestion_resolved: aviso de sugerencia aprobada/rechazada.
    - notif_reminder_minutes: minutos de anticipación para el recordatorio.
    - theme: tema visual (claro/oscuro).
    - language: idioma de la app (código ISO, ej. 'es', 'en').
    - app_purpose: propósito de uso definido en el tutorial inicial.
    - referred_by_friend: si llegó por referido.

    El updated_at se actualiza automáticamente via el TimestampMixin (onupdate).
    """
    configuracion = db.query(UserSettings).filter(
        UserSettings.id_user == current_user.id_user,
    ).first()

    if not configuracion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada. Contacta al soporte.",
        )

    campos = datos.model_dump(exclude_unset=True)

    if not campos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron campos para actualizar.",
        )

    # Validar notif_reminder_minutes si viene
    if "notif_reminder_minutes" in campos:
        minutos = campos["notif_reminder_minutes"]
        if minutos < 5 or minutos > 1440:  # Entre 5 minutos y 24 horas
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notif_reminder_minutes debe estar entre 5 y 1440 minutos (24 horas).",
            )

    # Validar language si viene (código ISO 639-1: 2 caracteres)
    if "language" in campos:
        if len(campos["language"].strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El idioma debe ser un código ISO válido (ej. 'es', 'en').",
            )

    for campo, valor in campos.items():
        setattr(configuracion, campo, valor)

    # Forzar updated_at ya que onupdate no siempre se dispara con setattr
    configuracion.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(configuracion)
    return configuracion