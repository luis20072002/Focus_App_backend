from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth import hash_password


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id_user == user_id, User.active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username, User.active == True).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email, User.active == True).first()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.query(User).filter(User.phone == phone, User.active == True).first()


def create_user(db: Session, data: UserCreate) -> User:
    # Verificar duplicados
    if data.email and get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo ya está registrado")
    if data.phone and get_user_by_phone(db, data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El teléfono ya está registrado")
    if get_user_by_username(db, data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya está en uso")

    user = User(
        name=data.name,
        lastname=data.lastname,
        username=data.username,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        birth_date=data.birth_date,
        profile_picture=data.profile_picture,
        description=data.description,
        private_profile=data.private_profile,
        id_role=3,  # Rol de usuario normal por defecto
        created_at=datetime.utcnow(),
        active=True
    )
    db.add(user)
    db.flush()  # Para obtener el id_user antes del commit

    # Crear configuracion por defecto
    settings = UserSettings(
        id_user=user.id_user,
        updated_at=datetime.utcnow()
    )
    db.add(settings)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, current_user: User) -> User:
    if current_user.id_user != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para editar este usuario")

    user = get_user_by_id(db, user_id)

    if data.email and data.email != user.email and get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo ya está registrado")
    if data.phone and data.phone != user.phone and get_user_by_phone(db, data.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El teléfono ya está registrado")
    if data.username and data.username != user.username and get_user_by_username(db, data.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre de usuario ya está en uso")

    update_data = data.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: int, current_user: User) -> None:
    if current_user.id_user != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para eliminar este usuario")

    user = get_user_by_id(db, user_id)
    user.active = False
    db.commit()