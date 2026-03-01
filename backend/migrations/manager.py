"""
数据库迁移管理器
统一管理所有数据库迁移，支持版本化迁移
"""
import os
import sqlite3
from typing import List, Dict
from core.database import engine, SQLALCHEMY_DATABASE_URL
from core.logging import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


class MigrationManager:
    """迁移管理器"""
    
    def __init__(self):
        self.db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
        self.migrations_table = "schema_migrations"
        self.migrations: List[Dict] = []
    
    def register_migration(self, version: str, description: str, up_func):
        """
        注册迁移
        
        Args:
            version: 迁移版本号（如 "001", "002"）
            description: 迁移描述
            up_func: 执行迁移的函数
        """
        self.migrations.append({
            "version": version,
            "description": description,
            "up": up_func
        })
        # 按版本号排序
        self.migrations.sort(key=lambda x: x["version"])
    
    def ensure_migrations_table(self):
        """确保迁移表存在"""
        if not os.path.exists(self.db_path):
            logger.warning(f"Database file not found: {self.db_path}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    version TEXT PRIMARY KEY,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()
    
    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移版本列表"""
        if not os.path.exists(self.db_path):
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT version FROM {self.migrations_table} ORDER BY version")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def mark_migration_applied(self, version: str, description: str):
        """标记迁移为已应用"""
        if not os.path.exists(self.db_path):
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"INSERT INTO {self.migrations_table} (version, description) VALUES (?, ?)",
                (version, description)
            )
            conn.commit()
        finally:
            conn.close()
    
    def run_migrations(self):
        """执行所有未应用的迁移"""
        self.ensure_migrations_table()
        applied = set(self.get_applied_migrations())
        
        logger.info("Checking for database migrations...")
        
        for migration in self.migrations:
            if migration["version"] in applied:
                logger.debug(f"Migration {migration['version']} already applied: {migration['description']}")
                continue
            
            logger.info(f"Applying migration {migration['version']}: {migration['description']}")
            try:
                with engine.connect() as conn:
                    migration["up"](conn)
                    conn.commit()
                self.mark_migration_applied(migration["version"], migration["description"])
                logger.info(f"Migration {migration['version']} applied successfully")
            except Exception as e:
                logger.error(f"Failed to apply migration {migration['version']}: {e}")
                raise


# 创建全局迁移管理器
migration_manager = MigrationManager()


# 注册所有迁移
def register_all_migrations():
    """注册所有迁移"""
    from sqlalchemy import text
    
    # Migration 001: 添加任务可靠性列
    def migration_001(conn):
        try:
            conn.execute(text("SELECT retry_count FROM tasks LIMIT 1"))
        except Exception:
            logger.info("Adding reliability columns to tasks table")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN retry_delay INTEGER DEFAULT 60"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN timeout INTEGER DEFAULT 3600"))
    
    migration_manager.register_migration("001", "Add reliability columns to tasks", migration_001)
    
    # Migration 002: 添加任务执行尝试列
    def migration_002(conn):
        try:
            conn.execute(text("SELECT attempt FROM task_executions LIMIT 1"))
        except Exception:
            logger.info("Adding attempt column to task_executions table")
            conn.execute(text("ALTER TABLE task_executions ADD COLUMN attempt INTEGER DEFAULT 1"))
    
    migration_manager.register_migration("002", "Add attempt column to task_executions", migration_002)
    
    # Migration 003: 添加优先级列
    def migration_003(conn):
        try:
            conn.execute(text("SELECT priority FROM tasks LIMIT 1"))
        except Exception:
            logger.info("Adding priority column to tasks table")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 0"))
    
    migration_manager.register_migration("003", "Add priority column to tasks", migration_003)
    
    # Migration 004: 添加资源监控列到 task_executions
    def migration_004(conn):
        try:
            conn.execute(text("SELECT max_cpu_percent FROM task_executions LIMIT 1"))
        except Exception:
            logger.info("Adding resource columns to task_executions table")
            conn.execute(text("ALTER TABLE task_executions ADD COLUMN max_cpu_percent FLOAT DEFAULT NULL"))
            conn.execute(text("ALTER TABLE task_executions ADD COLUMN max_memory_mb FLOAT DEFAULT NULL"))
    
    migration_manager.register_migration("004", "Add resource columns to task_executions", migration_004)
    
    # Migration 005: 添加限流列
    def migration_005(conn):
        try:
            conn.execute(text("SELECT request_interval FROM tasks LIMIT 1"))
        except Exception:
            logger.info("Adding rate limiting columns to tasks table")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN request_interval INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN max_requests_per_second INTEGER DEFAULT 0"))
    
    migration_manager.register_migration("005", "Add rate limiting columns to tasks", migration_005)
    
    # Migration 006: 添加熔断器列
    def migration_006(conn):
        try:
            conn.execute(text("SELECT consecutive_failures FROM tasks LIMIT 1"))
        except Exception:
            logger.info("Adding circuit breaker columns to tasks table")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN consecutive_failures INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN failure_threshold INTEGER DEFAULT 5"))
    
    migration_manager.register_migration("006", "Add circuit breaker columns to tasks", migration_006)
    
    # Migration 007: 添加资源限制列到 tasks
    def migration_007(conn):
        try:
            conn.execute(text("SELECT max_cpu_percent FROM tasks LIMIT 1"))
        except Exception:
            logger.info("Adding resource limit columns to tasks table")
            conn.execute(text("ALTER TABLE tasks ADD COLUMN max_cpu_percent INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE tasks ADD COLUMN max_memory_mb INTEGER DEFAULT 0"))
    
    migration_manager.register_migration("007", "Add resource limit columns to tasks", migration_007)
    
    # Migration 008: 添加项目输出目录列
    def migration_008(conn):
        try:
            conn.execute(text("SELECT output_dir FROM projects LIMIT 1"))
        except Exception:
            logger.info("Adding output_dir column to projects table")
            conn.execute(text("ALTER TABLE projects ADD COLUMN output_dir VARCHAR DEFAULT NULL"))
    
    migration_manager.register_migration("008", "Add output_dir column to projects", migration_008)
    
    # Migration 009: 添加 python_versions 表的列和索引调整
    def migration_009(conn):
        try:
            # Check if columns exist
            result = conn.execute(text("PRAGMA table_info(python_versions)"))
            columns = {row[1] for row in result}
            
            if "name" not in columns:
                logger.info("Adding 'name' column to python_versions")
                conn.execute(text("ALTER TABLE python_versions ADD COLUMN name VARCHAR DEFAULT ''"))
            
            if "is_conda" not in columns:
                logger.info("Adding 'is_conda' column to python_versions")
                conn.execute(text("ALTER TABLE python_versions ADD COLUMN is_conda BOOLEAN DEFAULT 0"))
            
            if "created_at" not in columns:
                logger.info("Adding 'created_at' column to python_versions")
                conn.execute(text("ALTER TABLE python_versions ADD COLUMN created_at DATETIME"))
                conn.execute(text("UPDATE python_versions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
            
            if "updated_at" not in columns:
                logger.info("Adding 'updated_at' column to python_versions")
                conn.execute(text("ALTER TABLE python_versions ADD COLUMN updated_at DATETIME"))
                conn.execute(text("UPDATE python_versions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
            
            # Double check for NULLs
            conn.execute(text("UPDATE python_versions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
            conn.execute(text("UPDATE python_versions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"))
            
            # Check and drop unique index on version column if exists
            result = conn.execute(text("PRAGMA index_list('python_versions')"))
            indexes = result.fetchall()
            for idx in indexes:
                # idx: (seq, name, unique, origin, partial)
                index_name = idx[1]
                is_unique = idx[2]
                if is_unique:
                    result2 = conn.execute(text(f"PRAGMA index_info('{index_name}')"))
                    col_info = result2.fetchall()
                    # col_info: (seqno, cid, name)
                    if len(col_info) == 1 and col_info[0][2] == 'version':
                        logger.info(f"Dropping unique index '{index_name}' on 'version' column")
                        conn.execute(text(f"DROP INDEX {index_name}"))
        except Exception as e:
            logger.warning(f"Migration 009 warning: {e}")
    
    migration_manager.register_migration("009", "Add columns and fix indexes for python_versions", migration_009)


# 初始化时注册所有迁移
register_all_migrations()
