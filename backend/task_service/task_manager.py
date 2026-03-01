"""
任务管理器 - 负责任务调度管理（APScheduler 封装）
"""
import json
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from core.database import SessionLocal
from core.config import settings
from core.logging import get_logger
from task_service import models
from task_service.task_executor import run_task_execution
from task_service.resource_monitor import resource_monitor
from task_service.process_manager import process_manager

logger = get_logger(__name__)


class TaskManager:
    """任务管理器 - 线程安全的单例，负责任务调度"""
    _instance = None
    _lock = threading.Lock()
    scheduler = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TaskManager, cls).__new__(cls)
            
            # High Performance Concurrency Config
            max_workers = settings.max_concurrent_tasks
            executors = {
                'default': ThreadPoolExecutor(max_workers),
                'processpool': ProcessPoolExecutor(5)
            }
            job_defaults = {
                'coalesce': settings.scheduler_coalesce,
                'max_instances': settings.scheduler_max_instances
            }
            
            logger.info(f"Initializing TaskManager with max_workers={max_workers}")
            cls._instance.scheduler = BackgroundScheduler(
                executors=executors,
                job_defaults=job_defaults
            )
        return cls._instance

    def start(self):
        """启动调度器和资源监控"""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            
            # Start resource monitor
            resource_monitor.start()
            logger.info("Resource monitor started")

    def shutdown(self):
        """关闭调度器和资源监控"""
        if self.scheduler and self.scheduler.running:
            resource_monitor.stop()
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    def add_job(self, task_id: int, trigger_type: str, trigger_value: str, status: str, priority: int = 0):
        """
        添加任务到调度器
        
        Args:
            task_id: 任务 ID
            trigger_type: 触发器类型（interval/cron/date/immediate）
            trigger_value: 触发器配置（JSON 字符串或 cron 表达式）
            status: 任务状态（只有 'active' 才会被调度）
            priority: 优先级（APScheduler 不直接支持，但可以存储）
        """
        # Remove existing job if any
        self.remove_job(task_id)
        
        if status != 'active':
            return

        trigger = None
        try:
            if trigger_type == 'interval':
                # trigger_value example: {"value": 1, "unit": "hours"}
                if isinstance(trigger_value, str):
                    val = json.loads(trigger_value)
                else:
                    val = trigger_value
                
                kwargs = {val['unit']: int(val['value'])}
                trigger = IntervalTrigger(**kwargs)
                
            elif trigger_type == 'cron':
                # trigger_value example: "* * * * *"
                trigger = CronTrigger.from_crontab(trigger_value)
                
            elif trigger_type == 'date':
                # trigger_value example: "2025-12-07T12:00:00"
                trigger = DateTrigger(run_date=trigger_value)
            
            elif trigger_type == 'immediate':
                return

            if trigger:
                self.scheduler.add_job(
                    run_task_execution,
                    trigger=trigger,
                    args=[task_id, 1, None, self.scheduler],
                    id=str(task_id),
                    replace_existing=True
                )
                logger.info(f"Job {task_id} added with trigger {trigger}")

        except Exception as e:
            logger.error(f"Failed to add job {task_id}: {e}")

    def remove_job(self, task_id: int):
        """从调度器中移除任务"""
        job_id = str(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    def pause_job(self, task_id: int):
        """暂停任务"""
        job_id = str(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)

    def resume_job(self, task_id: int):
        """恢复任务"""
        job_id = str(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            
    def get_next_run_time(self, task_id: int):
        """获取任务的下次运行时间"""
        job = self.scheduler.get_job(str(task_id))
        if job:
            return job.next_run_time
        return None

    def stop_execution(self, execution_id: int) -> bool:
        """
        停止正在运行的任务执行
        
        Args:
            execution_id: 执行 ID
            
        Returns:
            bool: 是否成功停止
        """
        return process_manager.stop_execution(execution_id)

    def load_jobs_from_db(self):
        """
        从数据库加载所有活跃任务并添加到调度器
        优化：批量加载，避免重复添加
        """
        db = SessionLocal()
        try:
            tasks = db.query(models.Task).filter(models.Task.status == 'active').all()
            logger.info(f"Loading {len(tasks)} active tasks from DB...")
            
            loaded_count = 0
            skipped_count = 0
            
            for task in tasks:
                # 检查任务是否已经在调度器中（避免重复添加）
                existing_job = self.scheduler.get_job(str(task.id))
                if existing_job:
                    skipped_count += 1
                    continue
                
                try:
                    self.add_job(
                        task.id,
                        task.trigger_type,
                        task.trigger_value,
                        task.status,
                        task.priority or 0
                    )
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to add job {task.id}: {e}")
            
            logger.info(f"Loaded {loaded_count} tasks, skipped {skipped_count} duplicates")
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
        finally:
            db.close()


# 全局单例实例
task_manager = TaskManager()
