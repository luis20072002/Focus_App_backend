from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv
import os

from app.database import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.userSCH import UserCreate, UserResponse
from dependencies import get_current_user

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


def hashear_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def crear_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(datos: UserCreate, db: Session = Depends(get_db)):
    if datos.email and db.query(User).filter(User.email == datos.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    if datos.phone and db.query(User).filter(User.phone == datos.phone).first():
        raise HTTPException(status_code=400, detail="El teléfono ya está registrado")
    if db.query(User).filter(User.username == datos.username).first():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")

    nuevo_usuario = User(
        name=datos.name,
        lastname=datos.lastname,
        username=datos.username,
        email=datos.email,
        phone=datos.phone,
        password_hash=hashear_password(datos.password),
        birth_date=datos.birth_date,
        profile_picture=datos.profile_picture,
        description=datos.description,
        private_profile=datos.private_profile,
        id_role=3,  # usuario normal por defecto
        created_at=datetime.utcnow(),
        active=True
    )
    db.add(nuevo_usuario)
    db.flush()

    configuracion = UserSettings(
        id_user=nuevo_usuario.id_user,
        updated_at=datetime.utcnow()
    )
    db.add(configuracion)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    identifier = form_data.username

    usuario = (
        db.query(User).filter(User.email == identifier, User.active == True).first()
        or db.query(User).filter(User.phone == identifier, User.active == True).first()
        or db.query(User).filter(User.username == identifier, User.active == True).first()
    )

    if not usuario or not verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not usuario.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta está desactivada")

    token = crear_token({"sub": str(usuario.id_user)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user