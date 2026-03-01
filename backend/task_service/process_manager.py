"""
进程管理模块 - 负责任务进程的启动、停止和进程组管理
"""
import os
import signal
import subprocess
import threading
import psutil
from typing import Dict, Optional
from core.logging import get_logger

logger = get_logger(__name__)


class ProcessManager:
    """进程管理器 - 线程安全的单例"""
    _instance = None
    _lock = threading.Lock()
    
    # 进程存储字典
    running_processes: Dict[int, subprocess.Popen] = {}  # execution_id -> subprocess.Popen
    process_groups: Dict[int, int] = {}  # execution_id -> process group ID (pgid)
    execution_stats: Dict[int, dict] = {}  # execution_id -> {'max_cpu': 0.0, 'max_mem': 0.0}
    psutil_processes: Dict[int, psutil.Process] = {}  # execution_id -> psutil.Process (cached)
    
    # Maximum cache size to prevent memory leaks
    MAX_CACHE_SIZE = 1000
    _cleanup_counter = 0  # Counter for periodic cleanup

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProcessManager, cls).__new__(cls)
                    cls._instance.running_processes = {}
                    cls._instance.process_groups = {}
                    cls._instance.execution_stats = {}
                    cls._instance.psutil_processes = {}
        return cls._instance

    def register_process(self, execution_id: int, process: subprocess.Popen):
        """注册一个正在运行的进程"""
        self.running_processes[execution_id] = process
        self.process_groups[execution_id] = process.pid
        logger.debug(f"Registered process {process.pid} for execution {execution_id}")

    def unregister_process(self, execution_id: int):
        """注销一个进程"""
        if execution_id in self.running_processes:
            del self.running_processes[execution_id]
        if execution_id in self.process_groups:
            del self.process_groups[execution_id]
        if execution_id in self.psutil_processes:
            del self.psutil_processes[execution_id]
        logger.debug(f"Unregistered process for execution {execution_id}")

    def stop_execution(self, execution_id: int) -> bool:
        """
        终止一个正在运行的执行进程及其所有子进程。
        使用进程组确保所有子进程都被终止。
        """
        if execution_id not in self.running_processes:
            return False
            
        process = self.running_processes[execution_id]
        try:
            # Kill the entire process group to ensure child processes are terminated
            pgid = self.process_groups.get(execution_id)
            if pgid:
                try:
                    # Kill the whole process group
                    os.killpg(pgid, signal.SIGTERM)
                    logger.info(f"Terminated process group {pgid} for execution {execution_id}")
                except ProcessLookupError:
                    # Process group may already be gone
                    pass
            else:
                # Fallback to single process kill
                process.terminate()
                logger.info(f"Terminated execution {execution_id}")

            return True
        except Exception as e:
            logger.error(f"Failed to terminate execution {execution_id}: {e}")
            return False

    def get_process(self, execution_id: int) -> Optional[subprocess.Popen]:
        """获取执行 ID 对应的进程对象"""
        return self.running_processes.get(execution_id)

    def is_running(self, execution_id: int) -> bool:
        """检查执行是否正在运行"""
        process = self.running_processes.get(execution_id)
        if process is None:
            return False
        return process.poll() is None

    def get_psutil_process(self, execution_id: int) -> Optional[psutil.Process]:
        """获取或创建 psutil Process 对象（带缓存）"""
        if execution_id in self.psutil_processes:
            return self.psutil_processes[execution_id]
        
        process = self.running_processes.get(execution_id)
        if process and process.poll() is None:
            try:
                pid = process.pid
                p = psutil.Process(pid)
                self.psutil_processes[execution_id] = p
                # First call always returns 0.0, so we just prime it
                p.cpu_percent(interval=None)
                return p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None
        return None

    def update_stats(self, execution_id: int, cpu: float, mem_mb: float):
        """更新执行统计信息"""
        if execution_id not in self.execution_stats:
            self.execution_stats[execution_id] = {'max_cpu': 0.0, 'max_mem': 0.0, 'last_update': 0}
        
        stats = self.execution_stats[execution_id]
        if cpu > stats['max_cpu']:
            stats['max_cpu'] = cpu
        if mem_mb > stats['max_mem']:
            stats['max_mem'] = mem_mb

    def get_stats(self, execution_id: int) -> Optional[dict]:
        """获取执行统计信息"""
        return self.execution_stats.get(execution_id)

    def cleanup_stats(self, execution_id: int):
        """清理执行统计信息"""
        if execution_id in self.execution_stats:
            del self.execution_stats[execution_id]

    def cleanup_caches(self):
        """
        清理过期的缓存条目，防止内存泄漏
        优化：使用更高效的清理策略，减少内存分配
        """
        try:
            # Get all running execution IDs (一次性获取，避免重复查询)
            running_ids = set(self.running_processes.keys())

            # 批量清理 stats 缓存
            stats_keys = list(self.execution_stats.keys())
            stale_stats = [exec_id for exec_id in stats_keys if exec_id not in running_ids]
            for exec_id in stale_stats:
                self.execution_stats.pop(exec_id, None)

            # 批量清理 psutil_processes 缓存
            psutil_keys = list(self.psutil_processes.keys())
            stale_psutil = [exec_id for exec_id in psutil_keys if exec_id not in running_ids]
            for exec_id in stale_psutil:
                self.psutil_processes.pop(exec_id, None)

            # Hard limit: if caches are too large, remove oldest entries (LRU-like)
            # 使用更智能的清理策略：保留最近使用的条目
            if len(self.execution_stats) > self.MAX_CACHE_SIZE:
                # 计算需要删除的数量（保留 50%）
                remove_count = len(self.execution_stats) - (self.MAX_CACHE_SIZE // 2)
                # 删除最旧的条目（字典顺序，Python 3.7+ 保持插入顺序）
                keys_to_remove = list(self.execution_stats.keys())[:remove_count]
                for k in keys_to_remove:
                    self.execution_stats.pop(k, None)
                    self.psutil_processes.pop(k, None)
                
                logger.debug(f"Cleaned up {remove_count} old cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")


# 全局单例实例
process_manager = ProcessManager()
