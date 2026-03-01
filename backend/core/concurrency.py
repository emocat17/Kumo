"""
并发控制模块 - 提供任务执行的并发控制机制
使用信号量限制同时执行的任务数量，防止资源耗尽
"""
import threading
from typing import Optional
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class ConcurrencyController:
    """并发控制器 - 使用信号量控制任务执行并发数"""
    
    _instance: Optional['ConcurrencyController'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConcurrencyController, cls).__new__(cls)
                    max_concurrent = settings.max_concurrent_tasks
                    cls._instance._semaphore = threading.Semaphore(max_concurrent)
                    cls._instance._active_count = 0
                    cls._instance._count_lock = threading.Lock()
                    logger.info(f"ConcurrencyController initialized with max_concurrent={max_concurrent}")
        return cls._instance
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        获取执行许可
        
        Args:
            timeout: 超时时间（秒），None 表示无限等待
            
        Returns:
            bool: 是否成功获取许可
        """
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._count_lock:
                self._active_count += 1
                logger.debug(f"Acquired execution slot. Active: {self._active_count}/{settings.max_concurrent_tasks}")
        return acquired
    
    def release(self):
        """释放执行许可"""
        with self._count_lock:
            if self._active_count > 0:
                self._active_count -= 1
        self._semaphore.release()
        logger.debug(f"Released execution slot. Active: {self._active_count}/{settings.max_concurrent_tasks}")
    
    def get_active_count(self) -> int:
        """获取当前活跃执行数"""
        with self._count_lock:
            return self._active_count
    
    def get_available_slots(self) -> int:
        """获取可用执行槽数"""
        return settings.max_concurrent_tasks - self.get_active_count()


# 全局单例实例
concurrency_controller = ConcurrencyController()
