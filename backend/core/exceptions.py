"""
统一异常处理模块 - 定义自定义异常类和错误码
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class KumoException(Exception):
    """Kumo 基础异常类"""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(KumoException):
    """资源未找到异常"""
    def __init__(self, resource: str, resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details or {}
        )


class ValidationError(KumoException):
    """数据验证异常"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field:
            message = f"Validation error in field '{field}': {message}"
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details or {}
        )


class ConflictError(KumoException):
    """资源冲突异常（如重复数据）"""
    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if resource:
            message = f"Conflict with {resource}: {message}"
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details or {}
        )


class UnauthorizedError(KumoException):
    """未授权异常"""
    def __init__(self, message: str = "Unauthorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            details=details or {}
        )


class ForbiddenError(KumoException):
    """禁止访问异常"""
    def __init__(self, message: str = "Forbidden", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            details=details or {}
        )


class DatabaseError(KumoException):
    """数据库操作异常"""
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if operation:
            message = f"Database error during {operation}: {message}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details or {}
        )


class FileSystemError(KumoException):
    """文件系统操作异常"""
    def __init__(self, message: str, path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if path:
            message = f"File system error at '{path}': {message}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="FILE_SYSTEM_ERROR",
            details=details or {}
        )


class ProcessError(KumoException):
    """进程操作异常"""
    def __init__(self, message: str, process_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if process_id:
            message = f"Process error for process '{process_id}': {message}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PROCESS_ERROR",
            details=details or {}
        )


class TimeoutError(KumoException):
    """操作超时异常"""
    def __init__(self, message: str = "Operation timeout", timeout: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if timeout:
            message = f"Operation timeout after {timeout} seconds"
        super().__init__(
            message=message,
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            error_code="TIMEOUT",
            details=details or {}
        )


class ServiceUnavailableError(KumoException):
    """服务不可用异常"""
    def __init__(self, message: str = "Service unavailable", service: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if service:
            message = f"Service '{service}' is unavailable"
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details or {}
        )
