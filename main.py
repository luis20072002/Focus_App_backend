from fastapi import FastAPI
from app.routers import auth, users, tasks, task_template, roles

app = FastAPI(
    title="Focus App API",
    description="API para la aplicación Focus App",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(task_template.router)
app.include_router(roles.router)


@app.get("/")
def root():
    return {"message": "Focus App API funcionando"}