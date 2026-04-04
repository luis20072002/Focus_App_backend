from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task_template import TaskTemplate
from app.models.template_category import TemplateCategory
from app.models.user import User
from app.schemas.task_template import TaskTemplateCreate, TaskTemplateUpdate, TaskTemplateResponse
from app.schemas.template_category import TemplateCategoryCreate, TemplateCategoryUpdate, TemplateCategoryResponse
from app.services.auth import get_current_active_user

router = APIRouter(prefix="/templates", tags=["Plantillas"])


# ── Categorias ───────────────────────────────────────────────────────────────

@router.get("/categories", response_model=list[TemplateCategoryResponse])
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return db.query(TemplateCategory).all()


@router.get("/categories/{category_id}", response_model=TemplateCategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    category = db.query(TemplateCategory).filter(TemplateCategory.id_category == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
    return category


@router.post("/categories", response_model=TemplateCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(data: TemplateCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    category = TemplateCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=TemplateCategoryResponse)
def update_category(category_id: int, data: TemplateCategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    category = db.query(TemplateCategory).filter(TemplateCategory.id_category == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    category = db.query(TemplateCategory).filter(TemplateCategory.id_category == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
    db.delete(category)
    db.commit()


# ── Plantillas de tareas ─────────────────────────────────────────────────────

@router.get("/", response_model=list[TaskTemplateResponse])
def get_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return db.query(TaskTemplate).filter(TaskTemplate.active == True).all()


@router.get("/{template_id}", response_model=TaskTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    template = db.query(TaskTemplate).filter(TaskTemplate.id_task_template == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
    return template


@router.post("/", response_model=TaskTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(data: TaskTemplateCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    category = db.query(TemplateCategory).filter(TemplateCategory.id_category == data.id_category).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La categoria especificada no existe")
    template = TaskTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.put("/{template_id}", response_model=TaskTemplateResponse)
def update_template(template_id: int, data: TaskTemplateUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    template = db.query(TaskTemplate).filter(TaskTemplate.id_task_template == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    template = db.query(TaskTemplate).filter(TaskTemplate.id_task_template == template_id).first()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
    db.delete(template)
    db.commit()