from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.follow import Follow
from app.models.notification import Notification
from app.models.user_badge import UserBadge
from app.models.user_settings import UserSettings
from app.models.verification_token import VerificationToken
from app.models.device_token import DeviceToken
from app.models.foint_transaction import FointTransaction
from app.models.ranking_history import RankingHistory
from app.models.template_suggestion import TemplateSuggestion
from app.schemas.userSCH import UserUpdate, UserResponse
from dependencies import get_current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/users", tags=["Usuarios"])


# ---------------------------------------------------------------------------
# GET /users/me — Ver mi propio perfil completo
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Devuelve el perfil completo del usuario autenticado.
    No requiere lógica adicional: get_current_user ya cargó el objeto desde BD.
    """
    return current_user


# ---------------------------------------------------------------------------
# PATCH /users/me — Editar mi perfil
# ---------------------------------------------------------------------------
@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    datos: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Edición parcial del perfil del usuario autenticado.

    Reglas:
    - private_profile NO se edita en esta entrega (se ignora si viene en el body).
    - username debe ser único en la BD.
    - email debe ser único en la BD (si se envía).
    - phone debe ser único en la BD (si se envía).
    - No se puede quedar sin email Y sin phone al mismo tiempo
      (validado en el schema UserUpdate).
    - Si se envía password, se hashea antes de guardar.
    - El usuario no puede cambiar su propio rol ni su estado active.
    """
    campos = datos.model_dump(exclude_unset=True)

    # Ignorar private_profile — no editable en esta entrega
    campos.pop("private_profile", None)

    # Validar unicidad de username (si viene y es distinto al actual)
    if "username" in campos and campos["username"] != current_user.username:
        existe = db.query(User).filter(
            User.username == campos["username"],
            User.id_user != current_user.id_user,
        ).first()
        if existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso",
            )

    # Validar unicidad de email (si viene y es distinto al actual)
    if "email" in campos and campos["email"] != current_user.email:
        existe = db.query(User).filter(
            User.email == campos["email"],
            User.id_user != current_user.id_user,
        ).first()
        if existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo ya está registrado",
            )

    # Validar unicidad de phone (si viene y es distinto al actual)
    if "phone" in campos and campos["phone"] != current_user.phone:
        existe = db.query(User).filter(
            User.phone == campos["phone"],
            User.id_user != current_user.id_user,
        ).first()
        if existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El teléfono ya está registrado",
            )

    # Garantizar que no queda sin método de contacto
    # (el schema ya bloquea enviar ambos en null explícitamente,
    # pero validamos el estado resultante por si se envía solo uno en null)
    email_final = campos.get("email", current_user.email)
    phone_final = campos.get("phone", current_user.phone)
    if email_final is None and phone_final is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes mantener al menos un correo o un número de teléfono",
        )

    # Hashear contraseña si viene
    if "password" in campos:
        campos["password_hash"] = pwd_context.hash(campos.pop("password"))

    # Aplicar cambios
    for campo, valor in campos.items():
        setattr(current_user, campo, valor)

    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# GET /users/search — Buscador de usuarios (RF-F21)
# ---------------------------------------------------------------------------
@router.get("/search", response_model=list[UserResponse])
def search_users(
    q: str = Query(..., min_length=1, description="Término de búsqueda (username, nombre o apellido)"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Busca usuarios activos por username, nombre o apellido.
    La búsqueda es case-insensitive y por coincidencia parcial (ILIKE).
    Se excluye al propio usuario de los resultados.
    Soporta paginación con limit/offset.
    """
    termino = f"%{q}%"

    usuarios = (
        db.query(User)
        .filter(
            User.active == True,
            User.id_user != current_user.id_user,
            or_(
                User.username.ilike(termino),
                User.name.ilike(termino),
                User.lastname.ilike(termino),
            ),
        )
        .order_by(User.username)
        .limit(limit)
        .offset(offset)
        .all()
    )

    return usuarios


# ---------------------------------------------------------------------------
# GET /users/{username} — Ver perfil público de otro usuario (RF-F13)
# ---------------------------------------------------------------------------
@router.get("/{username}", response_model=UserResponse)
def get_user_profile(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve el perfil de cualquier usuario activo por su username.
    En esta entrega private_profile siempre es False, así que todos
    los perfiles son accesibles. Cuando se active private_profile,
    aquí se añadirá la lógica de amistad mutua.

    Nota: la ruta /{username} va DESPUÉS de /search y /me en el router
    para que FastAPI no los interprete como parámetros de path.
    """
    usuario = db.query(User).filter(
        User.username == username,
        User.active == True,
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    return usuario


# ---------------------------------------------------------------------------
# DELETE /users/me — Eliminar cuenta (RF-F28 / RF-B12)
# ---------------------------------------------------------------------------
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina la cuenta del usuario autenticado y todos sus datos asociados.

    Orden de eliminación (respeta FK):
      1. FointTransaction       — referencia a Task y User
      2. Notification           — referencia a User
      3. DeviceToken            — referencia a User
      4. VerificationToken      — referencia a User
      5. UserBadge              — referencia a User
      6. RankingHistory         — referencia a User
      7. TemplateSuggestion     — referencia a User (como autor y como admin)
      8. Follow                 — referencia a User (como follower y followed)
      9. Task                   — referencia a User
      10. UserSettings          — referencia a User
      11. User                  — fila principal

    No se eliminan TaskTemplate ni Badge porque son datos globales del sistema.
    """
    uid = current_user.id_user

    # 1. Transacciones de Foints (referencia Task e User)
    db.query(FointTransaction).filter(FointTransaction.id_user == uid).delete()

    # 2. Notificaciones
    db.query(Notification).filter(Notification.id_user == uid).delete()

    # 3. Tokens de dispositivo (Firebase)
    db.query(DeviceToken).filter(DeviceToken.id_user == uid).delete()

    # 4. Tokens de verificación
    db.query(VerificationToken).filter(VerificationToken.id_user == uid).delete()

    # 5. Insignias del usuario
    db.query(UserBadge).filter(UserBadge.id_user == uid).delete()

    # 6. Historial de ranking
    db.query(RankingHistory).filter(RankingHistory.id_user == uid).delete()

    # 7. Sugerencias (como autor y como admin revisor)
    db.query(TemplateSuggestion).filter(TemplateSuggestion.id_user == uid).delete()
    db.query(TemplateSuggestion).filter(TemplateSuggestion.id_admin == uid).update(
        {"id_admin": None}
    )

    # 8. Relaciones de seguimiento (como seguidor y como seguido)
    db.query(Follow).filter(
        or_(Follow.id_follower == uid, Follow.id_followed == uid)
    ).delete()

    # 9. Tareas del usuario
    db.query(Task).filter(Task.id_user == uid).delete()

    # 10. Configuración
    db.query(UserSettings).filter(UserSettings.id_user == uid).delete()

    # 11. Usuario
    db.delete(current_user)

    db.commit()