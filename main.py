from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    authRT,
    usersRT,
    tasksRT,
    followsRT,
    notificationsRT,
    settingsRT,
    templatesRT,
    rankingRT,
    suggestionsRT,
    adminRT,
)
from app.routers.scheduler import scheduler, registrar_jobs


# ---------------------------------------------------------------------------
# Lifespan — arranca y detiene el scheduler junto con la app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    registrar_jobs()
    scheduler.start()
    print("[scheduler] APScheduler iniciado con 3 jobs activos.")
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    print("[scheduler] APScheduler detenido.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Focus App API",
    description="API para la aplicación Focus App",
    version="1.0.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(authRT.router)           # /auth
app.include_router(usersRT.router)          # /users
app.include_router(tasksRT.router)          # /tasks
app.include_router(followsRT.router)        # /follows
app.include_router(notificationsRT.router)  # /notifications
app.include_router(settingsRT.router)       # /settings
app.include_router(templatesRT.router)      # /categories  /templates
app.include_router(rankingRT.router)        # /ranking
app.include_router(suggestionsRT.router)    # /suggestions
app.include_router(adminRT.router)          # /admin


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Focus App API funcionando"}