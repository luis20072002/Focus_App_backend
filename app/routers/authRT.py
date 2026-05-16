from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv
import os
import random
import string
import resend  # pip install resend

from app.database import get_db
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.verification_token import VerificationToken, TokenType, TokenSendMethod
from app.schemas.userSCH import UserCreate, UserResponse
from app.schemas.verification_tokenSCH import PasswordResetConfirm, VerificationTokenVerify
from dependencies import get_current_user

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Focus App <noreply@focusapp.com>")

CODE_EXPIRE_MINUTES = 15

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


# ---------------------------------------------------------------------------
# Schemas locales
# ---------------------------------------------------------------------------

class PasswordRecoveryRequest(BaseModel):
    identifier: str  # email o teléfono con el que se registró el usuario


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def hashear_password(password: str) -> str:
    return pwd_context.hash(password)


def verificar_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def crear_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def generar_codigo_6_digitos() -> str:
    """Genera un código numérico de 6 dígitos como string."""
    return "".join(random.choices(string.digits, k=6))


def enviar_codigo_por_email(destinatario: str, codigo: str) -> None:
    """
    Envía el código de recuperación usando Resend.
    Variables de entorno requeridas: RESEND_API_KEY, EMAIL_FROM.
    """
    resend.api_key = RESEND_API_KEY
    resend.Emails.send({
        "from": EMAIL_FROM,
        "to": destinatario,
        "subject": "Tu código de recuperación — Focus App",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
            <h2>Recuperación de contraseña</h2>
            <p>Usa el siguiente código para restablecer tu contraseña.
               Expira en <strong>{CODE_EXPIRE_MINUTES} minutos</strong>.</p>
            <div style="font-size: 2rem; font-weight: bold; letter-spacing: 8px;
                        text-align: center; padding: 24px; background: #f4f4f4;
                        border-radius: 8px; margin: 24px 0;">
                {codigo}
            </div>
            <p style="color: #888; font-size: 0.85rem;">
                Si no solicitaste este código, ignora este mensaje.
            </p>
        </div>
        """,
    })


def invalidar_tokens_anteriores(id_user: int, tipo: TokenType, db: Session) -> None:
    """
    Marca como usados todos los tokens activos previos del mismo tipo.
    Evita que coexistan múltiples códigos válidos para el mismo usuario.
    """
    db.query(VerificationToken).filter(
        VerificationToken.id_user == id_user,
        VerificationToken.type == tipo,
        VerificationToken.used == False,
    ).update({"used": True})


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

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
        id_role=2,  # 1=Admin, 2=Usuario normal
        active=True,
    )
    db.add(nuevo_usuario)
    db.flush()

    configuracion = UserSettings(
        id_user=nuevo_usuario.id_user,
        updated_at=datetime.utcnow(),
    )
    db.add(configuracion)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

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
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )

    token = crear_token({"sub": str(usuario.id_user)})
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# POST /auth/password-recovery/request — Paso 1: Solicitar código (RF-F03)
# ---------------------------------------------------------------------------

@router.post(
    "/password-recovery/request",
    status_code=status.HTTP_200_OK,
    summary="Paso 1 — Solicitar código de recuperación",
)
def request_password_recovery(
    datos: PasswordRecoveryRequest,
    db: Session = Depends(get_db),
):
    """
    El usuario envía su email o teléfono registrado. El backend:
      1. Busca el usuario activo por email o teléfono.
      2. Responde siempre con el mismo mensaje (evita enumerar cuentas).
      3. Invalida tokens de recuperación anteriores no usados.
      4. Genera un código numérico de 6 dígitos.
      5. Persiste el token en BD con expiración de 15 minutos.
      6. Envía el código por email (SMS pendiente de implementar).

    No requiere JWT.
    """
    identifier = datos.identifier.strip()

    # Respuesta genérica — no revela si el identificador existe o no
    respuesta_generica = {
        "message": "Si el identificador está registrado, recibirás un código en tu correo."
    }

    usuario = (
        db.query(User).filter(User.email == identifier, User.active == True).first()
        or db.query(User).filter(User.phone == identifier, User.active == True).first()
    )

    if not usuario:
        return respuesta_generica

    # Si el usuario solo tiene teléfono y SMS no está implementado,
    # devolvemos la respuesta genérica para no revelar el estado de la cuenta
    if not usuario.email:
        return respuesta_generica

    # Invalidar tokens previos del mismo tipo para este usuario
    invalidar_tokens_anteriores(usuario.id_user, TokenType.password_recovery, db)

    # Generar código y persistir
    codigo = generar_codigo_6_digitos()
    nuevo_token = VerificationToken(
        id_user=usuario.id_user,
        token=codigo,
        type=TokenType.password_recovery,
        send_method=TokenSendMethod.email,
        used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES),
    )
    db.add(nuevo_token)
    db.commit()

    # Enviar por email — si falla, eliminar el token para permitir reintento
    try:
        enviar_codigo_por_email(usuario.email, codigo)
    except Exception:
        db.delete(nuevo_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo enviar el código. Intenta de nuevo más tarde.",
        )

    return respuesta_generica


# ---------------------------------------------------------------------------
# POST /auth/password-recovery/verify — Paso 2: Verificar código (RF-F03)
# ---------------------------------------------------------------------------

@router.post(
    "/password-recovery/verify",
    status_code=status.HTTP_200_OK,
    summary="Paso 2 — Verificar código recibido",
)
def verify_recovery_code(
    datos: VerificationTokenVerify,
    db: Session = Depends(get_db),
):
    """
    El usuario envía el código de 6 dígitos recibido. El backend:
      1. Busca el token activo (no usado, no expirado) que coincida.
      2. Si no existe o expiró, responde con 400.
      3. Marca el token como used=True — no puede reutilizarse para verificar.
      4. Devuelve el mismo código como reset_token para el paso 3.

    No requiere JWT.
    """
    token_db = db.query(VerificationToken).filter(
        VerificationToken.token == datos.token,
        VerificationToken.type == TokenType.password_recovery,
        VerificationToken.used == False,
        VerificationToken.expires_at > datetime.utcnow(),
    ).first()

    if not token_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código es inválido o ha expirado.",
        )

    # Marcar como usado — paso 3 lo buscará con used=True para confirmar
    # que el usuario pasó por la verificación y no saltó este paso
    token_db.used = True
    db.commit()

    return {
        "message": "Código verificado correctamente.",
        "reset_token": datos.token,
    }


# ---------------------------------------------------------------------------
# POST /auth/password-recovery/confirm — Paso 3: Nueva contraseña (RF-F03)
# ---------------------------------------------------------------------------

@router.post(
    "/password-recovery/confirm",
    status_code=status.HTTP_200_OK,
    summary="Paso 3 — Establecer nueva contraseña",
)
def confirm_password_reset(
    datos: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """
    El usuario envía el reset_token del paso 2 y su nueva contraseña. El backend:
      1. Busca el token con used=True (fue verificado) y aún no expirado.
         Esto evita saltar el paso 2 — un token no verificado tiene used=False.
      2. Valida la nueva contraseña (mínimo 8 caracteres, validado en schema).
      3. Hashea y guarda la nueva contraseña.
      4. Limpia tokens de recuperación residuales del usuario.
      5. El usuario debe hacer login nuevamente con su nueva contraseña.

    No requiere JWT.
    """
    token_db = db.query(VerificationToken).filter(
        VerificationToken.token == datos.token,
        VerificationToken.type == TokenType.password_recovery,
        VerificationToken.used == True,            # Verificado en paso 2
        VerificationToken.expires_at > datetime.utcnow(),  # Aún vigente
    ).first()

    if not token_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token es inválido, ha expirado o el código no fue verificado.",
        )

    usuario = db.query(User).filter(
        User.id_user == token_db.id_user,
        User.active == True,
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    # Actualizar contraseña
    usuario.password_hash = hashear_password(datos.new_password)

    # Limpieza defensiva: invalidar cualquier otro token de recuperación pendiente
    invalidar_tokens_anteriores(usuario.id_user, TokenType.password_recovery, db)

    db.commit()

    return {"message": "Contraseña actualizada correctamente. Inicia sesión con tu nueva contraseña."}