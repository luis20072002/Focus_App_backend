from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from app.database import get_db
from app.models.notification import Notification, NotificationType
from app.models.device_token import DeviceToken, DevicePlatform
from app.models.user import User
from app.schemas.notificationSCH import NotificationResponse
from app.schemas.device_tokenSCH import DeviceTokenCreate, DeviceTokenResponse
from dependencies import get_current_user

load_dotenv()

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


# ---------------------------------------------------------------------------
# Capa Firebase Cloud Messaging (FCM)
# ---------------------------------------------------------------------------
# Requiere en .env:
#   FIREBASE_CREDENTIALS_PATH=firebase_credentials.json
#
# Y en .gitignore:
#   firebase_credentials.json
#
# El archivo firebase_credentials.json se obtiene desde:
#   Firebase Console → Configuración del proyecto → Cuentas de servicio
#   → Generar nueva clave privada
# ---------------------------------------------------------------------------

_firebase_inicializado = False


def inicializar_firebase() -> None:
    """
    Inicializa el SDK de Firebase Admin una sola vez.
    Se llama lazy (solo cuando se va a enviar una notificación)
    para no bloquear el arranque si las credenciales no están configuradas.
    """
    global _firebase_inicializado
    if _firebase_inicializado:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials
        import json

        if not firebase_admin._apps:
            # Leer desde variable de entorno en lugar de archivo
            cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)

        _firebase_inicializado = True

    except Exception as e:
        raise RuntimeError(f"No se pudo inicializar Firebase: {e}")


def enviar_push(token_dispositivo: str, titulo: str, cuerpo: str, data: dict = None) -> bool:
    """
    Envía una notificación push a un dispositivo específico vía FCM.

    Parámetros:
    - token_dispositivo: FCM registration token del dispositivo.
    - titulo: Título visible de la notificación.
    - cuerpo: Texto de la notificación.
    - data: Payload adicional (opcional) para manejo en la app.

    Retorna True si se envió correctamente, False si el token es inválido.
    Los tokens inválidos deben eliminarse de la BD para no acumular basura.
    """
    inicializar_firebase()

    from firebase_admin import messaging

    mensaje = messaging.Message(
        notification=messaging.Notification(
            title=titulo,
            body=cuerpo,
        ),
        data=data or {},
        token=token_dispositivo,
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound="default",
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default"),
            ),
        ),
    )

    try:
        messaging.send(mensaje)
        return True
    except messaging.UnregisteredError:
        # Token inválido o el usuario desinstalió la app
        return False
    except Exception:
        # Otros errores de FCM (red, cuota, etc.) — no son fatales
        return False


def enviar_push_a_usuario(
    id_user: int,
    titulo: str,
    cuerpo: str,
    db: Session,
    data: dict = None,
) -> None:
    """
    Envía una notificación push a todos los dispositivos registrados de un usuario.
    Elimina automáticamente los tokens que FCM reporta como inválidos.

    Esta función es la que deben llamar otros routers (follows, tasks, etc.)
    cuando necesiten disparar una push. Importar así:

        from app.routes.notificationsRT import enviar_push_a_usuario
    """
    tokens = db.query(DeviceToken).filter(DeviceToken.id_user == id_user).all()

    tokens_invalidos = []
    for device in tokens:
        enviado = enviar_push(device.token, titulo, cuerpo, data)
        if not enviado:
            tokens_invalidos.append(device)

    # Limpiar tokens inválidos
    for device in tokens_invalidos:
        db.delete(device)

    if tokens_invalidos:
        db.commit()


def crear_notificacion_db(
    id_user: int,
    tipo: NotificationType,
    mensaje: str,
    db: Session,
    id_reference: int = None,
) -> Notification:
    """
    Persiste una notificación en la tabla notification.
    Llamar siempre junto a enviar_push_a_usuario para mantener
    el historial de notificaciones en BD.
    """
    notif = Notification(
        id_user=id_user,
        type=tipo,
        message=mensaje,
        id_reference=id_reference,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notificar_usuario(
    id_user: int,
    tipo: NotificationType,
    mensaje: str,
    titulo_push: str,
    db: Session,
    id_reference: int = None,
    data_push: dict = None,
) -> Notification:
    """
    Función principal para notificar a un usuario.
    Combina persistencia en BD + envío push en una sola llamada.

    Uso desde otros routers:
        from app.routes.notificationsRT import notificar_usuario

        notificar_usuario(
            id_user=usuario_seguido.id_user,
            tipo=NotificationType.new_follower,
            mensaje=f"@{current_user.username} ahora te sigue.",
            titulo_push="Nuevo seguidor",
            db=db,
            id_reference=current_user.id_user,
        )
    """
    notif = crear_notificacion_db(id_user, tipo, mensaje, db, id_reference)
    enviar_push_a_usuario(id_user, titulo_push, mensaje, db, data_push)
    return notif


# ---------------------------------------------------------------------------
# POST /notifications/device-token — Registrar token de dispositivo (RF-B10)
# ---------------------------------------------------------------------------

@router.post(
    "/device-token",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_device_token(
    datos: DeviceTokenCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registra o actualiza el token FCM del dispositivo del usuario.

    La app móvil debe llamar este endpoint:
    - Al iniciar sesión.
    - Cuando Firebase genere un nuevo token (onTokenRefresh).

    Si el token ya existe para otro usuario (cambio de dispositivo),
    se reasigna al usuario actual. Si ya existe para el mismo usuario,
    se devuelve sin duplicar.
    """
    # Si el token ya existe para este mismo usuario, devolver sin duplicar
    existente = db.query(DeviceToken).filter(
        DeviceToken.token == datos.token,
        DeviceToken.id_user == current_user.id_user,
    ).first()
    if existente:
        return existente

    # Si el token existe para otro usuario (dispositivo compartido/reasignado),
    # eliminar el registro anterior para evitar que otro usuario reciba las push
    otro = db.query(DeviceToken).filter(
        DeviceToken.token == datos.token,
        DeviceToken.id_user != current_user.id_user,
    ).first()
    if otro:
        db.delete(otro)

    nuevo = DeviceToken(
        id_user=current_user.id_user,
        token=datos.token,
        platform=datos.platform,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


# ---------------------------------------------------------------------------
# DELETE /notifications/device-token — Eliminar token al cerrar sesión
# ---------------------------------------------------------------------------

@router.delete("/device-token", status_code=status.HTTP_204_NO_CONTENT)
def unregister_device_token(
    token: str = Query(..., description="FCM token a eliminar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina el token FCM del dispositivo al cerrar sesión.
    La app móvil debe llamar este endpoint en el logout para que el usuario
    no siga recibiendo push en un dispositivo donde ya cerró sesión.
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.token == token,
        DeviceToken.id_user == current_user.id_user,
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token no encontrado.",
        )

    db.delete(device)
    db.commit()


# ---------------------------------------------------------------------------
# GET /notifications — Listar mis notificaciones (RF-F22)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[NotificationResponse])
def get_my_notifications(
    solo_no_leidas: bool = Query(False, description="Si True, devuelve solo las no leídas"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista las notificaciones del usuario autenticado.
    Ordenadas por fecha descendente (más recientes primero).
    Soporta filtro de no leídas y paginación.
    """
    q = db.query(Notification).filter(
        Notification.id_user == current_user.id_user,
    )

    if solo_no_leidas:
        q = q.filter(Notification.read == False)

    notificaciones = (
        q.order_by(Notification.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return notificaciones


# ---------------------------------------------------------------------------
# PATCH /notifications/{id_notification}/read — Marcar como leída
# ---------------------------------------------------------------------------

@router.patch("/{id_notification}/read", response_model=NotificationResponse)
def mark_notification_read(
    id_notification: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marca una notificación específica como leída.
    Solo el dueño de la notificación puede marcarla.
    """
    notif = db.query(Notification).filter(
        Notification.id_notification == id_notification,
        Notification.id_user == current_user.id_user,
    ).first()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    notif.read = True
    db.commit()
    db.refresh(notif)
    return notif


# ---------------------------------------------------------------------------
# PATCH /notifications/read-all — Marcar todas como leídas
# ---------------------------------------------------------------------------

@router.patch("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Marca todas las notificaciones no leídas del usuario como leídas.
    Útil para el botón 'Marcar todo como leído'.
    """
    actualizadas = db.query(Notification).filter(
        Notification.id_user == current_user.id_user,
        Notification.read == False,
    ).update({"read": True})

    db.commit()
    return {"message": f"{actualizadas} notificaciones marcadas como leídas."}


# ---------------------------------------------------------------------------
# DELETE /notifications/{id_notification} — Eliminar notificación
# ---------------------------------------------------------------------------

@router.delete("/{id_notification}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    id_notification: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina una notificación específica del usuario autenticado.
    """
    notif = db.query(Notification).filter(
        Notification.id_notification == id_notification,
        Notification.id_user == current_user.id_user,
    ).first()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    db.delete(notif)
    db.commit()