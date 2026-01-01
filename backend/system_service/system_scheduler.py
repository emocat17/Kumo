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
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "backups")
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
            # Load Config
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
