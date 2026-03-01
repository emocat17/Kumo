"""
统一配置管理模块
集中管理所有系统配置，支持环境变量覆盖
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """系统配置类"""
    
    model_config = ConfigDict(
        env_prefix="KUMO_",
        env_file=".env",
        case_sensitive=False
    )
    
    # ========== 路径配置 ==========
    # 基础目录（相对于 backend 目录）
    projects_dir: str = "./projects"
    data_dir: str = "./data"
    logs_dir: str = "./logs"
    envs_dir: str = "./envs"
    
    # 日志子目录
    task_log_dir: str = "./logs/tasks"
    install_log_dir: str = "./logs/install"
    
    # 备份目录
    backup_dir: str = "./data/backups"
    
    # ========== 数据库配置 ==========
    database_url: str = "sqlite:///./data/TaskManage.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_pre_ping: bool = True
    
    # ========== 调度器配置 ==========
    max_concurrent_tasks: int = 50
    scheduler_coalesce: bool = False
    scheduler_max_instances: int = 3
    
    # ========== 资源监控配置 ==========
    resource_monitor_interval: int = 2  # 监控间隔（秒）
    resource_update_interval: int = 10  # 数据库更新间隔（秒）
    
    # ========== 安全配置 ==========
    secret_key_file: str = "./data/secret.key"
    secret_key_env: str = "KUMO_SECRET_KEY"
    
    # ========== 系统配置 ==========
    timezone: str = "Asia/Shanghai"
    python_unbuffered: bool = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保路径是绝对路径
        self._normalize_paths()
    
    def _normalize_paths(self):
        """规范化路径，转换为绝对路径"""
        backend_dir = Path(__file__).parent.parent.absolute()
        
        def normalize_path(path: str) -> str:
            if os.path.isabs(path):
                return path
            if path.startswith("./"):
                return str(backend_dir / path[2:])
            return str(backend_dir / path)
        
        self.projects_dir = normalize_path(self.projects_dir)
        self.data_dir = normalize_path(self.data_dir)
        self.logs_dir = normalize_path(self.logs_dir)
        self.envs_dir = normalize_path(self.envs_dir)
        self.task_log_dir = normalize_path(self.task_log_dir)
        self.install_log_dir = normalize_path(self.install_log_dir)
        self.backup_dir = normalize_path(self.backup_dir)
        self.secret_key_file = normalize_path(self.secret_key_file)
        
        # 处理数据库路径
        if self.database_url.startswith("sqlite:///./"):
            db_path = self.database_url.replace("sqlite:///./", "")
            if not os.path.isabs(db_path):
                db_path = str(backend_dir / db_path)
            self.database_url = f"sqlite:///{db_path}"
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.projects_dir,
            self.data_dir,
            self.logs_dir,
            self.envs_dir,
            self.task_log_dir,
            self.install_log_dir,
            self.backup_dir,
            os.path.dirname(self.secret_key_file),
            os.path.dirname(self.database_url.replace("sqlite:///", ""))
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)


# 创建全局配置实例
settings = Settings()

# 确保目录存在
settings.ensure_directories()
