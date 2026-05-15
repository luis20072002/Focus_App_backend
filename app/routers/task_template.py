from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task_template import TaskTemplate
from app.models.template_category import TemplateCategory
from app.models.user import User
from app.schemas.task_templateSCH import TaskTemplateCreate, TaskTemplateUpdate, TaskTemplateResponse
from app.schemas.template_categorySCH import TemplateCategoryCreate, TemplateCategoryUpdate, TemplateCategoryResponse
from dependencies import get_current_user, solo_admin

router = APIRouter(prefix="/templates", tags=["Plantillas"])


# Categorias

@router.get("/categories", response_model=list[TemplateCategoryResponse])
def get_categorias(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(TemplateCategory).all()


@router.get("/categories/{category_id}", response_model=TemplateCategoryResponse)
def get_categoria(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    categoria = db.query(TemplateCategory).filter(TemplateCategory.id_category == category_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    return categoria


@router.post("/categories", response_model=TemplateCategoryResponse, status_code=201)
def crear_categoria(datos: TemplateCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    existe = db.query(TemplateCategory).filter(TemplateCategory.category_name == datos.category_name).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe una categoria con ese nombre")
    categoria = TemplateCategory(**datos.model_dump())
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@router.put("/categories/{category_id}", response_model=TemplateCategoryResponse)
def actualizar_categoria(
    category_id: int,
    datos: TemplateCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(solo_admin)
):
    categoria = db.query(TemplateCategory).filter(TemplateCategory.id_category == category_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")

    if datos.category_name is not None:
        existe = db.query(TemplateCategory).filter(
            TemplateCategory.category_name == datos.category_name,
            TemplateCategory.id_category != category_id
        ).first()
        if existe:
            raise HTTPException(status_code=400, detail="Ya existe una categoria con ese nombre")
        categoria.category_name = datos.category_name

    if datos.category_description is not None:
        categoria.category_description = datos.category_description

    db.commit()
    db.refresh(categoria)
    return categoria


@router.delete("/categories/{category_id}", status_code=200)
def eliminar_categoria(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    categoria = db.query(TemplateCategory).filter(TemplateCategory.id_category == category_id).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    db.delete(categoria)
    db.commit()
    return {"detail": "Categoria eliminada correctamente"}


#  Plantillas de tareas 

@router.get("/", response_model=list[TaskTemplateResponse])
def get_plantillas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(TaskTemplate).filter(TaskTemplate.active == True).all()


@router.get("/{template_id}", response_model=TaskTemplateResponse)
def get_plantilla(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    plantilla = db.query(TaskTemplate).filter(TaskTemplate.id_task_template == template_id).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return plantilla


@router.post("/", response_model=TaskTemplateResponse, status_code=201)
def crear_plantilla(datos: TaskTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    categoria = db.query(TemplateCategory).filter(TemplateCategory.id_category == datos.id_category).first()
    if not categoria:
        raise HTTPException(status_code=404, detail="La categoria especificada no existe")

    plantilla = TaskTemplate(**datos.model_dump())
    db.add(plantilla)
    db.commit()
    db.refresh(plantilla)
    return plantilla


@router.put("/{template_id}", response_model=TaskTemplateResponse)
def actualizar_plantilla(
    template_id: int,
    datos: TaskTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(solo_admin)
):
    plantilla = db.query(TaskTemplate).filter(TaskTemplate.id_task_template == template_id).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")

    if datos.id_category is not None:
        categoria = db.query(TemplateCategory).filter(TemplateCategory.id_category == datos.id_category).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="La categoria especificada no existe")
        plantilla.id_category = datos.id_category

    if datos.name is not None:
        plantilla.name = datos.name
    if datos.description is not None:
        plantilla.description = datos.description
    if datos.foints_base is not None:
        plantilla.foints_base = datos.foints_base
    if datos.active is not None:
        plantilla.active = datos.active

    db.commit()
    db.refresh(plantilla)
    return plantilla


@router.delete("/{template_id}", status_code=200)
def eliminar_plantilla(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(solo_admin)):
    plantilla = db.query(TaskTemplate).filter(TaskTemplate.id_task_template == template_id).first()
    if not plantilla:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    db.delete(plantilla)
    db.commit()
    return {"detail": "Plantilla eliminada correctamente"}