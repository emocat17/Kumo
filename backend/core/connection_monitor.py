"""
数据库连接监控模块 - 监控连接池状态和连接泄漏
"""
import threading
import time
from typing import Dict, Optional
from core.database import engine
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class ConnectionMonitor:
    """数据库连接监控器 - 监控连接池状态和潜在泄漏"""
    
    _instance: Optional['ConnectionMonitor'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConnectionMonitor, cls).__new__(cls)
                    cls._instance._running = False
                    cls._instance._thread = None
                    cls._instance._monitor_interval = 60  # 监控间隔（秒）
                    cls._instance._warning_threshold = 0.8  # 警告阈值（80%）
        return cls._instance
    
    def start(self):
        """启动连接监控"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Connection monitor started")
    
    def stop(self):
        """停止连接监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Connection monitor stopped")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                pool = engine.pool
                if pool:
                    size = pool.size()
                    checked_in = pool.checkedin()
                    checked_out = pool.checkedout()
                    overflow = pool.overflow()
                    invalid = pool.invalid()
                    
                    total_connections = size + overflow
                    used_connections = checked_out
                    available_connections = checked_in
                    
                    # 计算使用率
                    if total_connections > 0:
                        usage_percent = (used_connections / total_connections) * 100
                        
                        # 如果使用率超过阈值，记录警告
                        if usage_percent >= (self._warning_threshold * 100):
                            logger.warning(
                                f"Database connection pool usage high: {used_connections}/{total_connections} "
                                f"({usage_percent:.1f}%). Available: {available_connections}, "
                                f"Invalid: {invalid}, Overflow: {overflow}"
                            )
                        else:
                            logger.debug(
                                f"Database connection pool: {used_connections}/{total_connections} "
                                f"({usage_percent:.1f}%) used. Available: {available_connections}"
                            )
                    
                    # 检查无效连接
                    if invalid > 0:
                        logger.warning(f"Found {invalid} invalid database connections")
                
            except Exception as e:
                logger.error(f"Error monitoring database connections: {e}")
            
            time.sleep(self._monitor_interval)
    
    def get_pool_stats(self) -> Dict:
        """获取连接池统计信息"""
        try:
            pool = engine.pool
            if pool:
                return {
                    'size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                    'max_overflow': settings.database_max_overflow,
                    'pool_size': settings.database_pool_size
                }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
        return {}


# 全局单例实例
connection_monitor = ConnectionMonitor()
