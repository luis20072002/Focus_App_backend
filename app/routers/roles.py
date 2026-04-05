from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from dependencies import solo_admin

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleResponse])
def get_roles(db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    return db.query(Role).all()


@router.get("/{role_id}", response_model=RoleResponse)
def get_rol(role_id: int, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    rol = db.query(Role).filter(Role.id_role == role_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol


@router.post("/", response_model=RoleResponse, status_code=201)
def crear_rol(datos: RoleCreate, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    existe = db.query(Role).filter(Role.id_role == datos.id_role).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un rol con ese ID")
    rol = Role(**datos.model_dump())
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return rol


@router.put("/{role_id}", response_model=RoleResponse)
def actualizar_rol(
    role_id: int,
    datos: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(solo_admin)
):
    rol = db.query(Role).filter(Role.id_role == role_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    if datos.name_role is not None:
        rol.name_role = datos.name_role
    if datos.description is not None:
        rol.description = datos.description

    db.commit()
    db.refresh(rol)
    return rol


@router.delete("/{role_id}", status_code=200)
def eliminar_rol(role_id: int, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    rol = db.query(Role).filter(Role.id_role == role_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    db.delete(rol)
    db.commit()
    return {"detail": "Rol eliminado correctamente"}