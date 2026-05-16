from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.task_template import TaskTemplate
from app.models.template_category import TemplateCategory
from app.models.task import Task
from app.schemas.task_templateSCH import TaskTemplateCreate, TaskTemplateUpdate, TaskTemplateResponse
from app.schemas.template_categorySCH import TemplateCategoryCreate, TemplateCategoryUpdate, TemplateCategoryResponse
from dependencies import get_current_user, solo_admin
from app.models.user import User

router = APIRouter(tags=["Plantillas"])


# ===========================================================================
# CATEGORÍAS — prefix /categories
# ===========================================================================

category_router = APIRouter(prefix="/categories")


# ---------------------------------------------------------------------------
# GET /categories — Listar categorías (público para usuarios autenticados)
# ---------------------------------------------------------------------------

@category_router.get("", response_model=list[TemplateCategoryResponse])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las categorías de plantillas disponibles.
    Accesible por cualquier usuario autenticado — se usa en la pantalla
    de creación de tareas para mostrar el catálogo de plantillas (RF-F14).
    """
    return db.query(TemplateCategory).order_by(TemplateCategory.category_name).all()


# ---------------------------------------------------------------------------
# GET /categories/{id_category} — Ver categoría (público para usuarios autenticados)
# ---------------------------------------------------------------------------

@category_router.get("/{id_category}", response_model=TemplateCategoryResponse)
def get_category(
    id_category: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve una categoría específica por su ID.
    """
    categoria = db.query(TemplateCategory).filter(
        TemplateCategory.id_category == id_category,
    ).first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )

    return categoria


# ---------------------------------------------------------------------------
# POST /categories — Crear categoría (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@category_router.post("", response_model=TemplateCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    datos: TemplateCategoryCreate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Crea una nueva categoría de plantillas de tareas.
    Solo accesible por administradores (RF-A05).

    Validación: el nombre de la categoría debe ser único (case-insensitive).
    """
    existente = db.query(TemplateCategory).filter(
        TemplateCategory.category_name.ilike(datos.category_name.strip()),
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una categoría con ese nombre.",
        )

    nueva = TemplateCategory(
        category_name=datos.category_name.strip(),
        category_description=datos.category_description,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


# ---------------------------------------------------------------------------
# PATCH /categories/{id_category} — Editar categoría (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@category_router.patch("/{id_category}", response_model=TemplateCategoryResponse)
def update_category(
    id_category: int,
    datos: TemplateCategoryUpdate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Edición parcial de una categoría existente.
    Solo accesible por administradores (RF-A05).

    Si se cambia el nombre, se valida unicidad (case-insensitive).
    """
    categoria = db.query(TemplateCategory).filter(
        TemplateCategory.id_category == id_category,
    ).first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )

    campos = datos.model_dump(exclude_unset=True)

    if not campos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron campos para actualizar.",
        )

    # Validar unicidad del nombre si cambia
    if "category_name" in campos:
        nuevo_nombre = campos["category_name"].strip()
        existente = db.query(TemplateCategory).filter(
            TemplateCategory.category_name.ilike(nuevo_nombre),
            TemplateCategory.id_category != id_category,
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una categoría con ese nombre.",
            )
        campos["category_name"] = nuevo_nombre

    for campo, valor in campos.items():
        setattr(categoria, campo, valor)

    db.commit()
    db.refresh(categoria)
    return categoria


# ---------------------------------------------------------------------------
# DELETE /categories/{id_category} — Eliminar categoría (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@category_router.delete("/{id_category}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    id_category: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Elimina una categoría.
    Solo accesible por administradores (RF-A05).

    Restricción: no se puede eliminar si tiene plantillas asociadas
    (activas o inactivas). El admin debe desactivar o reasignar las
    plantillas antes de eliminar la categoría.
    """
    categoria = db.query(TemplateCategory).filter(
        TemplateCategory.id_category == id_category,
    ).first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )

    # Verificar que no tenga plantillas asociadas
    tiene_plantillas = db.query(TaskTemplate).filter(
        TaskTemplate.id_category == id_category,
    ).first()

    if tiene_plantillas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una categoría con plantillas asociadas. "
                   "Desactiva o reasigna las plantillas primero.",
        )

    db.delete(categoria)
    db.commit()


# ===========================================================================
# PLANTILLAS — prefix /templates
# ===========================================================================

template_router = APIRouter(prefix="/templates")


# ---------------------------------------------------------------------------
# GET /templates — Listar plantillas activas (público para usuarios autenticados)
# ---------------------------------------------------------------------------

@template_router.get("", response_model=list[TaskTemplateResponse])
def get_templates(
    id_category: Optional[int] = Query(None, description="Filtrar por categoría"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las plantillas de tareas activas.
    Soporta filtro opcional por categoría (?id_category=1).

    Usado en la pantalla de creación de tareas para mostrar el catálogo
    de plantillas disponibles agrupadas por categoría (RF-F14, RF-F15).
    Solo devuelve plantillas con active=True — las inactivas son invisibles
    para los usuarios normales.
    """
    q = db.query(TaskTemplate).filter(TaskTemplate.active == True)

    if id_category is not None:
        # Verificar que la categoría existe
        categoria = db.query(TemplateCategory).filter(
            TemplateCategory.id_category == id_category,
        ).first()
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada.",
            )
        q = q.filter(TaskTemplate.id_category == id_category)

    return q.order_by(TaskTemplate.name).all()


# ---------------------------------------------------------------------------
# GET /templates/all — Listar TODAS las plantillas (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@template_router.get("/all", response_model=list[TaskTemplateResponse])
def get_all_templates(
    id_category: Optional[int] = Query(None, description="Filtrar por categoría"),
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las plantillas (activas e inactivas).
    Exclusivo para administradores — usado en el panel de gestión (RF-A05).
    Soporta filtro opcional por categoría.
    """
    q = db.query(TaskTemplate)

    if id_category is not None:
        q = q.filter(TaskTemplate.id_category == id_category)

    return q.order_by(TaskTemplate.active.desc(), TaskTemplate.name).all()


# ---------------------------------------------------------------------------
# GET /templates/{id_task_template} — Ver plantilla (público para usuarios autenticados)
# ---------------------------------------------------------------------------

@template_router.get("/{id_task_template}", response_model=TaskTemplateResponse)
def get_template(
    id_task_template: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Devuelve una plantilla específica por su ID.
    Solo devuelve plantillas activas para usuarios normales.
    """
    plantilla = db.query(TaskTemplate).filter(
        TaskTemplate.id_task_template == id_task_template,
        TaskTemplate.active == True,
    ).first()

    if not plantilla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    return plantilla


# ---------------------------------------------------------------------------
# POST /templates — Crear plantilla (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@template_router.post("", response_model=TaskTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    datos: TaskTemplateCreate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Crea una nueva plantilla de tarea bajo una categoría existente.
    Solo accesible por administradores (RF-A05).

    Validaciones:
    - La categoría debe existir.
    - El nombre de la plantilla debe ser único dentro de la misma categoría
      (case-insensitive). Dos categorías distintas pueden tener el mismo nombre.
    - foints_base debe ser > 0 (validado en el schema).
    """
    # Verificar que la categoría existe
    categoria = db.query(TemplateCategory).filter(
        TemplateCategory.id_category == datos.id_category,
    ).first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada.",
        )

    # Verificar nombre único dentro de la categoría
    existente = db.query(TaskTemplate).filter(
        TaskTemplate.id_category == datos.id_category,
        TaskTemplate.name.ilike(datos.name.strip()),
    ).first()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una plantilla con ese nombre en esta categoría.",
        )

    nueva = TaskTemplate(
        id_category=datos.id_category,
        name=datos.name.strip(),
        description=datos.description,
        foints_base=datos.foints_base,
        active=datos.active,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


# ---------------------------------------------------------------------------
# PATCH /templates/{id_task_template} — Editar plantilla (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@template_router.patch("/{id_task_template}", response_model=TaskTemplateResponse)
def update_template(
    id_task_template: int,
    datos: TaskTemplateUpdate,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Edición parcial de una plantilla existente.
    Solo accesible por administradores (RF-A05).

    Permite desactivar una plantilla (active=False) sin eliminarla,
    lo que la hace invisible para los usuarios normales pero conserva
    el historial de tareas que ya la usaron.

    Si se cambia el nombre, se valida unicidad dentro de la categoría resultante.
    Si se cambia la categoría, se valida que exista.
    """
    plantilla = db.query(TaskTemplate).filter(
        TaskTemplate.id_task_template == id_task_template,
    ).first()

    if not plantilla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    campos = datos.model_dump(exclude_unset=True)

    if not campos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron campos para actualizar.",
        )

    # Verificar categoría si cambia
    id_category_final = campos.get("id_category", plantilla.id_category)
    if "id_category" in campos:
        categoria = db.query(TemplateCategory).filter(
            TemplateCategory.id_category == id_category_final,
        ).first()
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada.",
            )

    # Validar unicidad del nombre dentro de la categoría resultante
    if "name" in campos:
        nuevo_nombre = campos["name"].strip()
        existente = db.query(TaskTemplate).filter(
            TaskTemplate.id_category == id_category_final,
            TaskTemplate.name.ilike(nuevo_nombre),
            TaskTemplate.id_task_template != id_task_template,
        ).first()
        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una plantilla con ese nombre en esta categoría.",
            )
        campos["name"] = nuevo_nombre

    # Validar foints_base si viene
    if "foints_base" in campos and campos["foints_base"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="foints_base debe ser mayor que 0.",
        )

    for campo, valor in campos.items():
        setattr(plantilla, campo, valor)

    db.commit()
    db.refresh(plantilla)
    return plantilla


# ---------------------------------------------------------------------------
# DELETE /templates/{id_task_template} — Eliminar plantilla (solo admin, RF-A05)
# ---------------------------------------------------------------------------

@template_router.delete("/{id_task_template}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    id_task_template: int,
    current_user: User = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """
    Elimina una plantilla de tarea.
    Solo accesible por administradores (RF-A05).

    Restricción: no se puede eliminar si hay tareas (de cualquier usuario)
    que la referencian, para preservar la integridad del historial de Foints.
    En ese caso, usa PATCH para desactivarla (active=False).
    """
    plantilla = db.query(TaskTemplate).filter(
        TaskTemplate.id_task_template == id_task_template,
    ).first()

    if not plantilla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    # Verificar que no haya tareas que la referencien
    tiene_tareas = db.query(Task).filter(
        Task.id_task_template == id_task_template,
    ).first()

    if tiene_tareas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar una plantilla con tareas asociadas. "
                   "Desactívala con PATCH active=false en su lugar.",
        )

    db.delete(plantilla)
    db.commit()


# ===========================================================================
# Registrar ambos sub-routers en el router principal del módulo
# ===========================================================================

router.include_router(category_router)
router.include_router(template_router)