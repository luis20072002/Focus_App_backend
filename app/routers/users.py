from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from dependencies import get_current_user, solo_admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/users", tags=["Usuarios"])


def hashear_password(password: str) -> str:
    return pwd_context.hash(password)


@router.get("/", response_model=list[UserResponse])
def get_usuarios(db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    return db.query(User).filter(User.active == True).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_usuario(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    usuario = db.query(User).filter(User.id_user == user_id, User.active == True).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Si el perfil es privado, solo el mismo usuario o admin puede verlo
    if usuario.private_profile and current_user.id_user != user_id and current_user.id_role != 1:
        raise HTTPException(status_code=403, detail="Este perfil es privado")

    return usuario


@router.put("/{user_id}", response_model=UserResponse)
def actualizar_usuario(
    user_id: int,
    datos: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id_user != user_id and current_user.id_role != 1:
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este usuario")

    usuario = db.query(User).filter(User.id_user == user_id, User.active == True).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if datos.email and datos.email != usuario.email:
        if db.query(User).filter(User.email == datos.email).first():
            raise HTTPException(status_code=400, detail="El correo ya está registrado")
        usuario.email = datos.email

    if datos.phone and datos.phone != usuario.phone:
        if db.query(User).filter(User.phone == datos.phone).first():
            raise HTTPException(status_code=400, detail="El teléfono ya está registrado")
        usuario.phone = datos.phone

    if datos.username and datos.username != usuario.username:
        if db.query(User).filter(User.username == datos.username).first():
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
        usuario.username = datos.username

    if datos.name is not None:
        usuario.name = datos.name
    if datos.lastname is not None:
        usuario.lastname = datos.lastname
    if datos.birth_date is not None:
        usuario.birth_date = datos.birth_date
    if datos.profile_picture is not None:
        usuario.profile_picture = datos.profile_picture
    if datos.description is not None:
        usuario.description = datos.description
    if datos.private_profile is not None:
        usuario.private_profile = datos.private_profile
    if datos.password is not None:
        usuario.password_hash = hashear_password(datos.password)

    db.commit()
    db.refresh(usuario)
    return usuario

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"detail": "Sesion cerrada correctamente"}

@router.delete("/{user_id}", status_code=200)
def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id_user != user_id and current_user.id_role != 1:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este usuario")

    usuario = db.query(User).filter(User.id_user == user_id, User.active == True).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.active = False
    db.commit()
    return {"detail": "Cuenta eliminada correctamente"}