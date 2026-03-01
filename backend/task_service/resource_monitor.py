"""
资源监控模块 - 负责监控任务执行的 CPU 和内存使用情况
"""
import time
import threading
from core.database import SessionLocal
from core.config import settings
from core.logging import get_logger
from task_service import models
from task_service.process_manager import process_manager
import psutil

logger = get_logger(__name__)


class ResourceMonitor:
    """资源监控器 - 后台线程监控任务资源使用"""
    
    def __init__(self):
        self._running = False
        self._thread = None
        self._cleanup_counter = 0

    def start(self):
        """启动资源监控线程"""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Resource monitor started")

    def stop(self):
        """停止资源监控线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Resource monitor stopped")

    def _monitor_loop(self):
        """
        后台线程循环监控资源使用情况。
        使用批量更新来减少数据库操作。
        """
        while self._running:
            try:
                # Periodic cache cleanup every 60 iterations (approx. 60 seconds)
                self._cleanup_counter += 1
                if self._cleanup_counter >= 60:
                    process_manager.cleanup_caches()
                    self._cleanup_counter = 0

                # Iterate over a copy of keys to avoid runtime change issues
                exec_ids = list(process_manager.running_processes.keys())
                
                # Cleanup cache for finished processes
                cached_ids = list(process_manager.psutil_processes.keys())
                for cid in cached_ids:
                    if cid not in process_manager.running_processes:
                        del process_manager.psutil_processes[cid]

                # Collect updates for batch processing
                updates_needed = []
                now = time.time()
                update_interval = settings.resource_update_interval

                for exec_id in exec_ids:
                    process = process_manager.get_process(exec_id)
                    if process and process.poll() is None:
                        try:
                            # Get or Create cached psutil Process
                            p = process_manager.get_psutil_process(exec_id)
                            if p is None:
                                continue
                            
                            # Get stats (cpu_percent needs interval=None to be non-blocking)
                            # Subsequent calls on the SAME object return valid delta
                            cpu = p.cpu_percent(interval=None)
                            mem_info = p.memory_info()
                            mem_mb = mem_info.rss / (1024 * 1024)
                            
                            # Update stats
                            process_manager.update_stats(exec_id, cpu, mem_mb)
                            
                            # Collect updates for batch processing
                            stats = process_manager.get_stats(exec_id)
                            if stats:
                                last_update = stats.get('last_update', 0)
                                if now - last_update >= update_interval:
                                    updates_needed.append((exec_id, stats['max_cpu'], stats['max_mem']))
                                    
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Process might have died just now
                            if exec_id in process_manager.psutil_processes:
                                del process_manager.psutil_processes[exec_id]
                        except Exception as e:
                            logger.error(f"Error monitoring execution {exec_id}: {e}")
                
                # Batch update database - optimized for performance
                if updates_needed:
                    db = SessionLocal()
                    try:
                        # 批量查询所有需要更新的执行记录
                        exec_ids = [exec_id for exec_id, _, _ in updates_needed]
                        executions = db.query(models.TaskExecution).filter(
                            models.TaskExecution.id.in_(exec_ids)
                        ).all()
                        
                        # 构建更新映射
                        update_map = {exec_id: (max_cpu, max_mem) for exec_id, max_cpu, max_mem in updates_needed}
                        
                        # 批量更新执行记录
                        updated_count = 0
                        for execution in executions:
                            if execution.id in update_map:
                                max_cpu, max_mem = update_map[execution.id]
                                execution.max_cpu_percent = max_cpu
                                execution.max_memory_mb = max_mem
                                updated_count += 1
                                
                                # Update last_update timestamp in memory
                                stats = process_manager.get_stats(execution.id)
                                if stats:
                                    stats['last_update'] = now
                        
                        if updated_count > 0:
                            db.commit()
                            logger.debug(f"Batch updated {updated_count} execution stats")
                    except Exception as e:
                        logger.error(f"Error batch updating execution stats: {e}")
                        db.rollback()
                    finally:
                        db.close()
                        
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
                
            time.sleep(settings.resource_monitor_interval)


# 全局单例实例
resource_monitor = ResourceMonitor()
