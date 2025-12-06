from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from appEnv import models as env_models # Import models to ensure they are registered with Base

# Initialize DB tables
init_db()

from appEnv.python_version_router import router as python_version_router
from appEnv.env_router import router as env_router

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
