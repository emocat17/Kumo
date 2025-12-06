from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from appEnv import models as env_models # Import models to ensure they are registered with Base
from appProject import models as project_models # Register Project models

# Initialize DB tables
init_db()

from appEnv.python_version_router import router as python_version_router
from appEnv.env_router import router as env_router
from appProject.project_router import router as project_router
from appSystem.system_router import router as system_router
from appSystem.fs_router import router as fs_router

app = FastAPI()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
