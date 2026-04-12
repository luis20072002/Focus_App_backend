from fastapi import FastAPI
from app.routers import auth, users, tasks, task_template, roles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Focus App API",
    description="API para la aplicación Focus App",
    version="1.0.0",
    redirect_slashes=False
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(task_template.router)
app.include_router(roles.router)


@app.get("/")
def root():
    return {"message": "Focus App API funcionando"}