import os
import shutil
import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from core.database import SessionLocal, SQLALCHEMY_DATABASE_URL
from system_service import models as system_models

logger = logging.getLogger("system_scheduler")

# Define Paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BACKEND_DIR, "data", "backups")
LOG_DIR = os.path.join(BACKEND_DIR, "logs")
TASK_LOG_DIR = os.path.join(LOG_DIR, "tasks")
INSTALL_LOG_DIR = os.path.join(LOG_DIR, "install")

DB_PATH = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
if DB_PATH.startswith("./"):
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DB_PATH[2:])

class SystemScheduler:
    _instance = None
    scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemScheduler, cls).__new__(cls)
            cls._instance.scheduler = BackgroundScheduler()
        return cls._instance

    def start(self):
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("System Scheduler started.")
            self.refresh_jobs()

    def shutdown(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("System Scheduler shutdown.")

    def refresh_jobs(self):
        """Reload backup configuration and reschedule jobs"""
        logger.info("Refreshing system jobs...")
        self.scheduler.remove_all_jobs()

        db: Session = SessionLocal()
        try:
            # Load Config - Backup
            enabled = self._get_config(db, "backup.enabled", "false") == "true"
            interval_hours = int(self._get_config(db, "backup.interval_hours", "24"))

            if enabled:
                logger.info(f"Scheduling auto-backup every {interval_hours} hours.")
                self.scheduler.add_job(
                    self._backup_job,
                    trigger=IntervalTrigger(hours=interval_hours),
                    id="auto_backup",
                    replace_existing=True,
                    next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10) # Run soon after start
                )
            else:
                logger.info("Auto-backup is disabled.")

            # Load Config - Log Cleanup
            log_cleanup_enabled = self._get_config(db, "log_cleanup.enabled", "false") == "true"
            log_cleanup_days = int(self._get_config(db, "log_cleanup.days", "7"))

            if log_cleanup_enabled:
                logger.info(f"Scheduling log cleanup every {log_cleanup_days} days.")
                self.scheduler.add_job(
                    self._cleanup_logs_job,
                    trigger=IntervalTrigger(days=1),  # Run daily, check age in job
                    id="log_cleanup",
                    replace_existing=True,
                    next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=1)
                )
            else:
                logger.info("Log cleanup is disabled.")

            # Load Config - Execution Cleanup
            exec_cleanup_enabled = self._get_config(db, "exec_cleanup.enabled", "false") == "true"
            exec_cleanup_days = int(self._get_config(db, "exec_cleanup.days", "30"))

            if exec_cleanup_enabled:
                logger.info(f"Scheduling execution cleanup every {exec_cleanup_days} days.")
                self.scheduler.add_job(
                    self._cleanup_executions_job,
                    trigger=IntervalTrigger(days=1),  # Run daily
                    id="exec_cleanup",
                    replace_existing=True,
                    next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=2)
                )
            else:
                logger.info("Execution cleanup is disabled.")

        except Exception as e:
            logger.error(f"Error refreshing system jobs: {e}")
        finally:
            db.close()

    def _get_config(self, db: Session, key: str, default: str) -> str:
        config = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == key).first()
        return config.value if config else default

    def _backup_job(self):
        """Execute Backup Logic"""
        logger.info("Executing auto-backup...")
        db: Session = SessionLocal()
        try:
            # 1. Ensure backup dir exists
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)

            # 2. Create Backup
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"TaskManage_Auto_{timestamp}.db"
            dest_path = os.path.join(BACKUP_DIR, filename)
            
            # Using sqlite3 online backup API would be better for active DBs, 
            # but shutil.copy is acceptable for this scale if we accept potential (rare) inconsistency.
            # Ideally, we should use WAL mode or SQLAlchemy connection to backup.
            # For simplicity in this "small feature", file copy is used.
            shutil.copy2(DB_PATH, dest_path)
            logger.info(f"Backup created: {filename}")

            # 3. Retention Policy
            retention_count = int(self._get_config(db, "backup.retention_count", "7"))
            self._cleanup_old_backups(retention_count)
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
        finally:
            db.close()

    def _cleanup_old_backups(self, retention_count: int):
        """Keep only the latest N backups"""
        try:
            backups = []
            for f in os.listdir(BACKUP_DIR):
                if f.endswith(".db") and "Auto" in f: # Only manage auto backups
                    path = os.path.join(BACKUP_DIR, f)
                    backups.append((path, os.path.getmtime(path)))

            # Sort by time desc (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)

            if len(backups) > retention_count:
                to_delete = backups[retention_count:]
                for path, _ in to_delete:
                    os.remove(path)
                    logger.info(f"Deleted old backup: {os.path.basename(path)}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def _cleanup_logs_job(self):
        """Clean up old task and install logs"""
        logger.info("Executing log cleanup...")
        db: Session = SessionLocal()
        try:
            # Get retention days from config
            days = int(self._get_config(db, "log_cleanup.days", "7"))
            cutoff_time = datetime.datetime.now().timestamp() - (days * 86400)

            deleted_count = 0

            # Clean up task logs
            if os.path.exists(TASK_LOG_DIR):
                for f in os.listdir(TASK_LOG_DIR):
                    if f.endswith(".log"):
                        path = os.path.join(TASK_LOG_DIR, f)
                        try:
                            if os.path.getmtime(path) < cutoff_time:
                                os.remove(path)
                                deleted_count += 1
                                logger.info(f"Deleted old task log: {f}")
                        except Exception as e:
                            logger.error(f"Error deleting task log {f}: {e}")

            # Clean up install logs
            if os.path.exists(INSTALL_LOG_DIR):
                for f in os.listdir(INSTALL_LOG_DIR):
                    if f.endswith(".log"):
                        path = os.path.join(INSTALL_LOG_DIR, f)
                        try:
                            if os.path.getmtime(path) < cutoff_time:
                                os.remove(path)
                                deleted_count += 1
                                logger.info(f"Deleted old install log: {f}")
                        except Exception as e:
                            logger.error(f"Error deleting install log {f}: {e}")

            logger.info(f"Log cleanup completed. Deleted {deleted_count} files.")

        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")
        finally:
            db.close()

    def _cleanup_executions_job(self):
        """Clean up old task execution records"""
        logger.info("Executing execution cleanup...")
        from task_service import models as task_models

        db: Session = SessionLocal()
        try:
            # Get retention days from config
            days = int(self._get_config(db, "exec_cleanup.days", "30"))
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

            # Find old executions to delete (not running ones)
            old_executions = db.query(task_models.TaskExecution).filter(
                task_models.TaskExecution.status.notin_(['running', 'pending']),
                task_models.TaskExecution.end_time < cutoff_date
            ).all()

            deleted_count = 0
            for exec_record in old_executions:
                # Delete associated log file if exists
                if exec_record.log_file and os.path.exists(exec_record.log_file):
                    try:
                        os.remove(exec_record.log_file)
                        logger.debug(f"Deleted log file: {exec_record.log_file}")
                    except Exception as e:
                        logger.error(f"Error deleting log file {exec_record.log_file}: {e}")

                db.delete(exec_record)
                deleted_count += 1

            db.commit()
            logger.info(f"Execution cleanup completed. Deleted {deleted_count} execution records.")

        except Exception as e:
            logger.error(f"Execution cleanup failed: {e}")
            db.rollback()
        finally:
            db.close()
