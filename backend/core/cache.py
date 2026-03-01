"""
查询缓存模块 - 为频繁查询提供缓存层
使用简单的内存缓存，支持 TTL（Time To Live）
"""
import time
import threading
from typing import Any, Optional, Dict, Callable
from core.logging import get_logger

logger = get_logger(__name__)


class QueryCache:
    """查询缓存 - 线程安全的内存缓存"""
    
    _instance: Optional['QueryCache'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(QueryCache, cls).__new__(cls)
                    cls._instance._cache: Dict[str, tuple[Any, float]] = {}
                    cls._instance._cache_lock = threading.RLock()
                    cls._instance._max_size = 1000  # 最大缓存条目数
                    cls._instance._default_ttl = 60  # 默认 TTL（秒）
        return cls._instance
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        with self._cache_lock:
            if key not in self._cache:
                return None
            
            value, expire_time = self._cache[key]
            if time.time() > expire_time:
                del self._cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值
        """
        if ttl is None:
            ttl = self._default_ttl
        
        expire_time = time.time() + ttl
        
        with self._cache_lock:
            # 如果缓存已满，删除最旧的条目
            if len(self._cache) >= self._max_size:
                self._cleanup_expired()
                # 如果仍然满，删除最旧的条目
                if len(self._cache) >= self._max_size:
                    oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]
            
            self._cache[key] = (value, expire_time)
    
    def delete(self, key: str):
        """删除缓存键"""
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """清空所有缓存"""
        with self._cache_lock:
            self._cache.clear()
    
    def _cleanup_expired(self):
        """清理过期条目"""
        now = time.time()
        expired_keys = [
            key for key, (_, expire_time) in self._cache.items()
            if now > expire_time
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._cache_lock:
            self._cleanup_expired()
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'usage_percent': (len(self._cache) / self._max_size) * 100
            }


# 全局单例实例
query_cache = QueryCache()
