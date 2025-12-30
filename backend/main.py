from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import init_db, engine
from sqlalchemy import text
from environment_service import models as env_models # Import models to ensure they are registered with Base
from project_service import models as project_models # Register Project models
from task_service import models as task_models # Register Task models
from system_service import models as system_models # Register System models
from task_service.task_manager import task_manager

def run_migrations():
    print("Checking for schema migrations...")
    with engine.connect() as conn:
        # Check if retry_count exists in tasks
        try:
            conn.execute(text("SELECT retry_count FROM tasks LIMIT 1"))
        except Exception:
            print("Migrating tasks table: adding reliability columns")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN retry_delay INTEGER DEFAULT 60"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN timeout INTEGER DEFAULT 3600"))
            
        # Check if attempt exists in task_executions
        try:
            conn.execute(text("SELECT attempt FROM task_executions LIMIT 1"))
        except Exception:
            print("Migrating task_executions table: adding attempt column")
            conn.execute(text("ALTER TABLE task_executions ADD COLUMN attempt INTEGER DEFAULT 1"))
            
        # Check if priority exists in tasks
        try:
            conn.execute(text("SELECT priority FROM tasks LIMIT 1"))
        except Exception:
            print("Migrating tasks table: adding priority column")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 0"))

        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    try:
        init_db()
        run_migrations()
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

from environment_service.python_version_router import router as python_version_router
from environment_service.env_router import router as env_router
from project_service.project_router import router as project_router
from system_service.system_router import router as system_router
from system_service.env_vars_router import router as env_vars_router
from system_service.fs_router import router as fs_router
from task_service.task_router import router as task_router
from log_service.logs_router import router as logs_router

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
app.include_router(env_vars_router, prefix="/api/system/env-vars", tags=["Environment Variables"])
app.include_router(fs_router, prefix="/api")
app.include_router(task_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
