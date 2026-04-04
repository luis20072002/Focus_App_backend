from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import verify_password, create_access_token, get_current_active_user
from app.services.users import create_user, get_user_by_email, get_user_by_username, get_user_by_phone
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, data)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # El campo username de OAuth2PasswordRequestForm lo usamos para correo, telefono o nombre de usuario
    identifier = form_data.username

    user: User | None = (
        get_user_by_email(db, identifier)
        or get_user_by_phone(db, identifier)
        or get_user_by_username(db, identifier)
    )

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta está desactivada")

    access_token = create_access_token(data={"sub": user.id_user})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user