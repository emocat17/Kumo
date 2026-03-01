from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError as PydanticValidationError
from core.database import init_db, engine
from core.logging import get_logger, setup_logging
from core.config import settings
from core.exceptions import KumoException
from core.connection_monitor import connection_monitor
from core.error_handlers import (
    kumo_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    pydantic_validation_exception_handler,
    value_error_handler,
    global_exception_handler
)
from environment_service import models as env_models # Import models to ensure they are registered with Base
from project_service import models as project_models # Register Project models
from system_service import models as system_models # Register System models
from audit_service import models as audit_models # Register Audit models
from task_service import models as task_models # Register Task models
from task_service.task_manager import task_manager
from system_service.system_scheduler import get_system_scheduler
from migrations.manager import migration_manager

# 初始化日志系统
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Kumo backend...")
    try:
        init_db()
        logger.info("Database tables initialized")
        
        # 运行迁移
        migration_manager.run_migrations()
        logger.info("Database migrations completed")
        
        task_manager.start()
        task_manager.load_jobs_from_db()
        logger.info("Task manager started")
        
        system_scheduler = get_system_scheduler()
        system_scheduler.start()
        logger.info("System scheduler started")
        
        # 启动连接监控器
        connection_monitor.start()
        logger.info("Connection monitor started")
        
        logger.info("Kumo backend started successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise e
    yield
    # Shutdown
    logger.info("Shutting down Kumo backend...")
    connection_monitor.stop()
    task_manager.shutdown()
    system_scheduler = get_system_scheduler()
    system_scheduler.shutdown()
    logger.info("Kumo backend shutdown complete")

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
    
    # 添加连接池统计信息
    try:
        pool_stats = connection_monitor.get_pool_stats()
        if pool_stats:
            health_status["connection_pool"] = pool_stats
    except Exception:
        pass
    
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

# 统一异常处理器注册
# 注意：异常处理器的注册顺序很重要，应该从最具体到最通用

@app.exception_handler(KumoException)
async def handle_kumo_exception(request: Request, exc: KumoException):
    """Kumo 自定义异常处理器"""
    return await kumo_exception_handler(request, exc)

@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    """HTTP 异常处理器"""
    return await http_exception_handler(request, exc)

@app.exception_handler(SQLAlchemyError)
async def handle_sqlalchemy_exception(request: Request, exc: SQLAlchemyError):
    """SQLAlchemy 异常处理器"""
    return await sqlalchemy_exception_handler(request, exc)

@app.exception_handler(PydanticValidationError)
async def handle_pydantic_validation_exception(request: Request, exc: PydanticValidationError):
    """Pydantic 验证异常处理器"""
    return await pydantic_validation_exception_handler(request, exc)

@app.exception_handler(ValueError)
async def handle_value_error(request: Request, exc: ValueError):
    """ValueError 异常处理器"""
    return await value_error_handler(request, exc)

@app.exception_handler(Exception)
async def handle_global_exception(request: Request, exc: Exception):
    """全局异常处理器 - 捕获所有未处理的异常"""
    return await global_exception_handler(request, exc)

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
