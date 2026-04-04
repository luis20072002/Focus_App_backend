from fastapi import FastAPI

from app.routers import auth as auth_router
from app.routers import users as users_router
from app.routers import tasks as tasks_router
from app.routers import task_template as task_template_router
from app.routers import roles as roles_router
app = FastAPI(
    title="Focus App API",
    description="API para Focus App",
    version="1.0.0"
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(tasks_router.router)
app.include_router(task_template_router.router)
app.include_router(roles_router.router)


@app.get("/")
def root():
    return {"message": "Focus App API funcionando"}