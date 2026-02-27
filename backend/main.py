from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.database import init_db, engine
from sqlalchemy import text
from environment_service import models as env_models # Import models to ensure they are registered with Base
from project_service import models as project_models # Register Project models
from system_service import models as system_models # Register System models
from audit_service import models as audit_models # Register Audit models
from task_service import models as task_models # Register Task models
from task_service.task_manager import task_manager
from system_service.system_scheduler import SystemScheduler

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

        # Check if max_cpu_percent exists in task_executions
        try:
            conn.execute(text("SELECT max_cpu_percent FROM task_executions LIMIT 1"))
        except Exception:
            print("Migrating task_executions table: adding resource columns")
            conn.execute(text("ALTER TABLE task_executions ADD COLUMN max_cpu_percent FLOAT DEFAULT NULL"))
            conn.execute(text("ALTER TABLE task_executions ADD COLUMN max_memory_mb FLOAT DEFAULT NULL"))

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
        SystemScheduler().start()
        print("System scheduler started.")
    except Exception as e:
        print(f"Startup failed: {e}")
        raise e
    yield
    # Shutdown
    print("Shutting down...")
    task_manager.shutdown()
    SystemScheduler().shutdown()

from environment_service.python_version_router import router as python_version_router
from environment_service.env_router import router as env_router
from project_service.project_router import router as project_router
from system_service.system_router import router as system_router
from system_service.env_vars_router import router as env_vars_router
from system_service.fs_router import router as fs_router
from task_service.task_router import router as task_router
from log_service.logs_router import router as logs_router
from audit_service.audit_router import router as audit_router

app = FastAPI(title="Kumo Backend", version="1.0.0", lifespan=lifespan)

# CORS 配置 - 生产环境应该限制具体域名
# 开发环境允许本地端口
cors_origins = [
    "http://localhost:18080",  # 前端开发服务器
    "http://localhost:5173",   # Vite 默认端口
    "http://127.0.0.1:18080",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查端点
@app.get("/api/health")
async def health_check():
    """系统健康检查"""
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "scheduler": "unknown",
    }
    
    # 检查数据库
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # 检查调度器
    if task_manager.scheduler and task_manager.scheduler.running:
        health_status["scheduler"] = "running"
    else:
        health_status["scheduler"] = "stopped"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)

# 版本信息端点
@app.get("/api/version")
async def get_version():
    """获取系统版本信息"""
    return {
        "version": "1.0.0",
        "name": "Kumo",
        "description": "Python 任务调度与全栈环境管理平台"
    }

# 全局异常处理器

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理 - 提供统一的错误响应格式"""
    import traceback
    
    # 返回安全的错误信息，不暴露内部细节
    error_message = str(exc)
    
    # 对于常见错误类型，提供友好提示
    if "unique constraint" in error_message.lower():
        detail = "数据已存在，请检查输入是否重复"
    elif "foreign key constraint" in error_message.lower():
        detail = "关联数据不存在，请检查引用的资源"
    elif "timeout" in error_message.lower():
        detail = "操作超时，请稍后重试"
    else:
        detail = "服务器内部错误，请稍后重试"
    
    # 记录完整错误到日志（不在响应中返回）
    print(f"[ERROR] {request.method} {request.url.path}: {error_message}")
    print(f"[TRACE] {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": detail,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理 - 统一格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path)
        }
    )

app.include_router(python_version_router, prefix="/api/python/versions")
app.include_router(env_router, prefix="/api/python/environments")
app.include_router(project_router, prefix="/api/projects", tags=["Projects"])
app.include_router(system_router, prefix="/api/system")
app.include_router(env_vars_router, prefix="/api/system/env-vars", tags=["Environment Variables"])
app.include_router(fs_router, prefix="/api")
app.include_router(task_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])
app.include_router(audit_router, prefix="/api/audit", tags=["Audit"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
