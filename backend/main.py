from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from appEnv import models as env_models # Import models to ensure they are registered with Base
from appProject import models as project_models # Register Project models
from appTask import models as task_models # Register Task models
from appTask.task_manager import task_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    try:
        init_db()
        print("Database initialized.")
        task_manager.start()
        task_manager.load_jobs_from_db()
        print("Task manager started.")
    except Exception as e:
        print(f"Startup failed: {e}")
        raise e
    yield
    # Shutdown
    print("Shutting down...")
    task_manager.shutdown()

from appEnv.python_version_router import router as python_version_router
from appEnv.env_router import router as env_router
from appProject.project_router import router as project_router
from appSystem.system_router import router as system_router
from appSystem.fs_router import router as fs_router
from appTask.task_router import router as task_router
from appLogs.logs_router import router as logs_router

app = FastAPI(title="Kumo Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(python_version_router, prefix="/api/python/versions")
app.include_router(env_router, prefix="/api/python/environments")
app.include_router(project_router, prefix="/api/projects", tags=["Projects"])
app.include_router(system_router, prefix="/api/system")
app.include_router(fs_router, prefix="/api")
app.include_router(task_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
