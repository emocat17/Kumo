"""
统一错误处理模块 - 提供统一的异常处理器和错误响应格式
"""
import traceback
from typing import Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from pydantic import ValidationError as PydanticValidationError
from core.exceptions import KumoException
from core.logging import get_logger

logger = get_logger(__name__)


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    path: str,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    创建统一的错误响应
    
    Args:
        status_code: HTTP 状态码
        error_code: 错误代码
        message: 错误消息
        path: 请求路径
        details: 额外详情
    
    Returns:
        JSONResponse: 统一的错误响应
    """
    response_data: Dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": message,
            "path": path
        }
    }
    
    if details:
        response_data["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def kumo_exception_handler(request: Request, exc: KumoException) -> JSONResponse:
    """Kumo 自定义异常处理器"""
    logger.warning(
        f"{request.method} {request.url.path}: {exc.error_code} - {exc.message}",
        extra={"error_code": exc.error_code, "details": exc.details}
    )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        path=str(request.url.path),
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 异常处理器 - 统一格式"""
    error_code = "HTTP_ERROR"
    
    # 根据状态码映射错误代码
    status_code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        408: "TIMEOUT",
        413: "PAYLOAD_TOO_LARGE",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    
    error_code = status_code_mapping.get(exc.status_code, "HTTP_ERROR")
    
    logger.warning(
        f"{request.method} {request.url.path}: {error_code} - {exc.detail}",
        extra={"status_code": exc.status_code}
    )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=str(exc.detail),
        path=str(request.url.path)
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """SQLAlchemy 异常处理器"""
    error_message = str(exc)
    
    # 处理完整性约束错误
    if isinstance(exc, IntegrityError):
        error_code = "DATABASE_INTEGRITY_ERROR"
        message = "数据完整性约束错误"
        
        # 检查是否是唯一约束
        if "unique constraint" in error_message.lower() or "UNIQUE constraint" in error_message:
            message = "数据已存在，请检查输入是否重复"
            error_code = "DUPLICATE_ENTRY"
        # 检查是否是外键约束
        elif "foreign key constraint" in error_message.lower() or "FOREIGN KEY constraint" in error_message:
            message = "关联数据不存在，请检查引用的资源"
            error_code = "FOREIGN_KEY_VIOLATION"
        # 检查是否是非空约束
        elif "NOT NULL constraint" in error_message or "not null constraint" in error_message.lower():
            message = "必填字段不能为空"
            error_code = "NOT_NULL_VIOLATION"
    # 处理操作错误（如连接失败）
    elif isinstance(exc, OperationalError):
        error_code = "DATABASE_OPERATIONAL_ERROR"
        message = "数据库操作失败，请稍后重试"
    else:
        error_code = "DATABASE_ERROR"
        message = "数据库操作错误"
    
    logger.error(
        f"{request.method} {request.url.path}: Database error - {error_message}",
        exc_info=True
    )
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=error_code,
        message=message,
        path=str(request.url.path)
    )


async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Pydantic 验证异常处理器"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"{request.method} {request.url.path}: Validation error - {len(errors)} field(s) invalid"
    )
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="请求数据验证失败",
        path=str(request.url.path),
        details={"fields": errors}
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """ValueError 异常处理器"""
    error_message = str(exc)
    
    logger.warning(
        f"{request.method} {request.url.path}: ValueError - {error_message}"
    )
    
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code="INVALID_VALUE",
        message=error_message or "无效的值",
        path=str(request.url.path)
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器 - 捕获所有未处理的异常"""
    error_message = str(exc)
    error_type = type(exc).__name__
    
    # 记录完整错误信息到日志
    logger.error(
        f"{request.method} {request.url.path}: Unhandled exception ({error_type}) - {error_message}",
        exc_info=True
    )
    
    # 根据错误类型提供友好的错误消息
    if "timeout" in error_message.lower() or "timed out" in error_message.lower():
        detail = "操作超时，请稍后重试"
        error_code = "TIMEOUT"
        status_code = status.HTTP_408_REQUEST_TIMEOUT
    elif "permission" in error_message.lower() or "access denied" in error_message.lower():
        detail = "权限不足，无法执行此操作"
        error_code = "PERMISSION_DENIED"
        status_code = status.HTTP_403_FORBIDDEN
    elif "not found" in error_message.lower():
        detail = "请求的资源不存在"
        error_code = "NOT_FOUND"
        status_code = status.HTTP_404_NOT_FOUND
    else:
        detail = "服务器内部错误，请稍后重试"
        error_code = "INTERNAL_SERVER_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return create_error_response(
        status_code=status_code,
        error_code=error_code,
        message=detail,
        path=str(request.url.path)
    )
