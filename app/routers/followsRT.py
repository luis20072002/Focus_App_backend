from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.follow import Follow
from app.models.user import User
from app.models.notification import Notification, NotificationType
from app.routers.notificationsRT import notificar_usuario
from app.schemas.followSCH import FollowCreate, FollowResponse
from app.schemas.userSCH import UserResponse
from dependencies import get_current_user

router = APIRouter(prefix="/follows", tags=["Seguimiento"])


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def existe_follow(id_follower: int, id_followed: int, db: Session) -> Follow | None:
    """Devuelve el Follow si existe, None si no."""
    return db.query(Follow).filter(
        Follow.id_follower == id_follower,
        Follow.id_followed == id_followed,
    ).first()


def son_amigos(id_a: int, id_b: int, db: Session) -> bool:
    """
    Dos usuarios son amigos si se siguen mutuamente.
    """
    a_sigue_b = existe_follow(id_a, id_b, db)
    b_sigue_a = existe_follow(id_b, id_a, db)
    return bool(a_sigue_b and b_sigue_a)


# ---------------------------------------------------------------------------
# POST /follows — Seguir a un usuario (RF-F20)
# ---------------------------------------------------------------------------

@router.post("", response_model=FollowResponse, status_code=status.HTTP_201_CREATED)
def follow_user(
    datos: FollowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    El usuario autenticado sigue al usuario con id_followed.

    Validaciones:
    - No puede seguirse a sí mismo (también lo bloquea el CheckConstraint de BD).
    - No puede seguir a alguien que ya sigue.
    - El usuario a seguir debe existir y estar activo.

    Efecto secundario (RF-B10 / RF-F22):
    - Crea una Notification de tipo new_follower para el usuario seguido.
    """
    if datos.id_followed == current_user.id_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes seguirte a ti mismo.",
        )

    # Verificar que el usuario a seguir existe y está activo
    usuario_seguido = db.query(User).filter(
        User.id_user == datos.id_followed,
        User.active == True,
    ).first()

    if not usuario_seguido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    # Verificar que no lo sigue ya
    if existe_follow(current_user.id_user, datos.id_followed, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya sigues a este usuario.",
        )

    # Crear el follow
    nuevo_follow = Follow(
        id_follower=current_user.id_user,
        id_followed=datos.id_followed,
    )
    db.add(nuevo_follow)
    db.flush()

    # Notificación al usuario seguido (RF-F22)
    notificar_usuario(
    id_user=datos.id_followed,
    tipo=NotificationType.new_follower,
    mensaje=f"@{current_user.username} ahora te sigue.",
    titulo_push="Nuevo seguidor",
    db=db,
    id_reference=current_user.id_user,
)


    db.commit()
    db.refresh(nuevo_follow)
    return nuevo_follow


# ---------------------------------------------------------------------------
# DELETE /follows/{id_followed} — Dejar de seguir (RF-F12)
# ---------------------------------------------------------------------------

@router.delete("/{id_followed}", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_user(
    id_followed: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    El usuario autenticado deja de seguir al usuario con id_followed.
    Si eran amigos (seguimiento mutuo), la amistad se rompe automáticamente
    al eliminar este follow.
    """
    follow = existe_follow(current_user.id_user, id_followed, db)

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sigues a este usuario.",
        )

    db.delete(follow)
    db.commit()


# ---------------------------------------------------------------------------
# GET /follows/followers — Mis seguidores (RF-F12)
# ---------------------------------------------------------------------------

@router.get("/followers", response_model=list[UserResponse])
def get_my_followers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista los usuarios que siguen al usuario autenticado.
    Ordenados por fecha de seguimiento descendente (más recientes primero).
    """
    seguidores = (
        db.query(User)
        .join(Follow, Follow.id_follower == User.id_user)
        .filter(
            Follow.id_followed == current_user.id_user,
            User.active == True,
        )
        .order_by(Follow.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return seguidores


# ---------------------------------------------------------------------------
# GET /follows/following — A quiénes sigo (RF-F12)
# ---------------------------------------------------------------------------

@router.get("/following", response_model=list[UserResponse])
def get_my_following(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista los usuarios que el usuario autenticado sigue.
    Ordenados por fecha de seguimiento descendente (más recientes primero).
    """
    seguidos = (
        db.query(User)
        .join(Follow, Follow.id_followed == User.id_user)
        .filter(
            Follow.id_follower == current_user.id_user,
            User.active == True,
        )
        .order_by(Follow.date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return seguidos


# ---------------------------------------------------------------------------
# GET /follows/friends — Amigos mutuos (RF-F12)
# ---------------------------------------------------------------------------

@router.get("/friends", response_model=list[UserResponse])
def get_my_friends(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lista los usuarios con los que hay seguimiento mutuo (amigos).
    Un amigo es alguien a quien sigo Y que también me sigue.

    Se obtienen cruzando:
    - Usuarios que yo sigo (Follow con id_follower=yo)
    - Usuarios que me siguen (Follow con id_followed=yo)
    y quedándonos con la intersección.
    """
    # Subquery: IDs de usuarios que yo sigo
    yo_sigo = db.query(Follow.id_followed).filter(
        Follow.id_follower == current_user.id_user
    ).subquery()

    # Subquery: IDs de usuarios que me siguen
    me_siguen = db.query(Follow.id_follower).filter(
        Follow.id_followed == current_user.id_user
    ).subquery()

    # Intersección: usuarios en ambos conjuntos = amigos
    amigos = (
        db.query(User)
        .filter(
            User.id_user.in_(yo_sigo),
            User.id_user.in_(me_siguen),
            User.active == True,
        )
        .order_by(User.username)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return amigos


# ---------------------------------------------------------------------------
# DELETE /follows/followers/{id_follower} — Eliminar un seguidor (RF-F12)
# ---------------------------------------------------------------------------

@router.delete("/followers/{id_follower}", status_code=status.HTTP_204_NO_CONTENT)
def remove_follower(
    id_follower: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina a un usuario de los seguidores del usuario autenticado.
    Es decir, fuerza que id_follower deje de seguir a current_user.

    Esto es diferente a unfollow: aquí el autenticado es el seguido,
    no el seguidor. Útil para el botón 'Eliminar seguidor' de RF-F12.

    Si eran amigos, la amistad se rompe automáticamente.
    """
    follow = existe_follow(id_follower, current_user.id_user, db)

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este usuario no te sigue.",
        )

    db.delete(follow)
    db.commit()