from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.auth import get_current_active_user
from app.services.users import get_user_by_id, update_user, deactivate_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return update_user(db, user_id, data, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    deactivate_user(db, user_id, current_user)