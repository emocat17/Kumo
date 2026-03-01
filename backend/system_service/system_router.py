import platform
import time
import psutil
import os
import shutil
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db, SQLALCHEMY_DATABASE_URL, Base, engine
from environment_service import models as env_models
from project_service import models as project_models
from task_service import models as task_models
from task_service.task_manager import task_manager
from system_service import models as system_models
from system_service import schemas as system_schemas
from system_service.system_scheduler import SystemScheduler
from fastapi.responses import FileResponse

router = APIRouter()

# Record application start time
APP_START_TIME = time.time()

# Backup Settings
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "backups")
DB_PATH = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
if DB_PATH.startswith("./"):
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DB_PATH[2:])

def get_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f} {unit}{suffix}"
        bytes /= factor

def remove_readonly(func, path, excinfo):
    os.chmod(path, 0o777)
    func(path)

def clear_directory(path: str):
    removed = []
    if not os.path.exists(path):
        return removed
    for entry in os.scandir(path):
        target = entry.path
        try:
            if entry.is_dir():
                shutil.rmtree(target, onerror=remove_readonly)
            else:
                os.remove(target)
            removed.append(target)
        except Exception:
            pass
    return removed

# --- Configuration Endpoints ---

@router.get("/config", response_model=List[system_schemas.SystemConfig])
async def get_all_configs(db: Session = Depends(get_db)):
    """
    获取所有系统配置
    
    返回系统中所有配置项，包括备份配置、代理配置、PyPI 镜像等。
    
    **返回**: 配置项列表，每个配置项包含：
    - id: 配置 ID
    - key: 配置键名
    - value: 配置值
    - description: 配置描述
    
    **示例返回**:
    ```json
    [
        {
            "id": 1,
            "key": "backup.enabled",
            "value": "true",
            "description": "是否启用自动备份"
        },
        {
            "id": 2,
            "key": "backup.interval",
            "value": "24",
            "description": "备份间隔（小时）"
        }
    ]
    ```
    """
    return db.query(system_models.SystemConfig).all()

@router.post("/config", response_model=system_schemas.SystemConfig)
async def create_or_update_config(config: system_schemas.SystemConfigCreate, db: Session = Depends(get_db)):
    """
    创建或更新系统配置
    
    如果配置键已存在则更新，否则创建新配置。
    
    **参数**:
    - **key**: 配置键名（必填）
    - **value**: 配置值（必填）
    - **description**: 配置描述（可选）
    
    **特殊处理**:
    - 如果配置键以 `backup.` 开头，会自动刷新备份调度器
    
    **返回**: 创建或更新后的配置对象
    
    **示例请求**:
    ```json
    {
        "key": "backup.enabled",
        "value": "true",
        "description": "是否启用自动备份"
    }
    ```
    
    **返回示例**:
    ```json
    {
        "id": 1,
        "key": "backup.enabled",
        "value": "true",
        "description": "是否启用自动备份"
    }
    ```
    """
    db_config = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == config.key).first()
    if db_config:
        db_config.value = config.value
        if config.description:
            db_config.description = config.description
    else:
        db_config = system_models.SystemConfig(
            key=config.key,
            value=config.value,
            description=config.description
        )
        db.add(db_config)
    
    db.commit()
    db.refresh(db_config)
    
    # Trigger scheduler refresh if backup config changed
    if config.key.startswith("backup."):
        SystemScheduler().refresh_jobs()
        
    return db_config

@router.get("/config/{key}", response_model=system_schemas.SystemConfig)
async def get_config_by_key(key: str, db: Session = Depends(get_db)):
    """
    根据键名获取系统配置
    
    **参数**:
    - **key**: 配置键名（路径参数）
    
    **返回**: 配置对象
    
    **错误响应**:
    - `404`: 配置不存在
    
    **示例请求**:
    ```
    GET /api/system/config/backup.enabled
    ```
    """
    config = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

# --- System Info Endpoints ---

@router.get("/info")
async def get_system_info(db: Session = Depends(get_db)):
    """
    获取系统基本信息
    
    返回系统的统计信息和运行状态，包括：
    - 环境数量
    - 项目数量
    - 系统运行时间
    - 系统信息（操作系统、Python 版本等）
    
    **返回**:
    ```json
    {
        "env_count": 5,
        "project_count": 10,
        "uptime_minutes": 120,
        "system_info": {
            "system": "Linux",
            "node": "hostname",
            "release": "5.4.0",
            "version": "#1 SMP",
            "machine": "x86_64",
            "processor": "x86_64",
            "python_version": "3.12.9"
        }
    }
    ```
    
    **说明**:
    - `uptime_minutes`: 系统运行时间（分钟），从应用启动时开始计算
    - `system_info`: 使用 `platform.uname()` 获取的系统信息
    """
    # 1. Environment Count
    env_count = db.query(env_models.PythonVersion).count()
    
    # 2. Project Count
    project_count = db.query(project_models.Project).count()
    
    # 3. Uptime
    uptime_seconds = time.time() - APP_START_TIME
    uptime_minutes = int(uptime_seconds / 60)
    
    # 4. System Info
    uname = platform.uname()
    sys_info = {
        "system": uname.system,
        "node": uname.node,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor,
        "python_version": platform.python_version()
    }
    
    return {
        "env_count": env_count,
        "project_count": project_count,
        "uptime_minutes": uptime_minutes,
        "system_info": sys_info
    }

# --- Backup Endpoints ---

@router.post("/backup")
async def create_backup():
    """
    手动创建数据库备份
    
    立即创建数据库的备份文件，保存到备份目录。
    
    **备份位置**: `backend/data/backups/`
    
    **备份文件名格式**: `TaskManage_backup_YYYYMMDD_HHMMSS.db`
    
    **返回**:
    ```json
    {
        "message": "Backup created successfully",
        "filename": "TaskManage_backup_20240101_120000.db",
        "path": "/path/to/backups/TaskManage_backup_20240101_120000.db",
        "size": "1.20 MB",
        "created_at": "2024-01-01T12:00:00"
    }
    ```
    
    **错误响应**:
    - `500`: 数据库文件不存在或备份失败
    
    **注意**: 
    - 备份使用文件复制方式，在数据库有大量写入时可能不够安全
    - 建议在低负载时进行备份
    """
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"TaskManage_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Check if DB file exists
        if not os.path.exists(DB_PATH):
             raise HTTPException(status_code=500, detail="Database file not found on disk")
             
        # Use shutil to copy
        # Note: Copying SQLite while running is generally safe for read-only backup but can be corrupted if heavy writes.
        # Ideally we should use sqlite3 API to backup, but simple copy is often enough for small apps.
        # Or better: "sqlite3 TaskManage.db .dump > backup.sql" but that requires sqlite3 CLI.
        # Let's try simple copy first.
        shutil.copy2(DB_PATH, backup_path)
        
        stat = os.stat(backup_path)
        return {
            "message": "Backup created successfully",
            "filename": backup_filename,
            "path": backup_path,
            "size": get_size(stat.st_size),
            "created_at": datetime.datetime.fromtimestamp(stat.st_mtime)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@router.get("/backups")
async def list_backups():
    """
    列出所有可用的备份文件
    
    返回备份目录中所有备份文件的列表，按创建时间倒序排列。
    
    **返回**: 备份文件列表，每个备份包含：
    - filename: 文件名
    - size: 文件大小（格式化）
    - size_raw: 文件大小（字节）
    - created_at: 创建时间
    
    **返回示例**:
    ```json
    [
        {
            "filename": "TaskManage_backup_20240101_120000.db",
            "size": "1.20 MB",
            "size_raw": 1258291,
            "created_at": "2024-01-01T12:00:00"
        },
        {
            "filename": "TaskManage_backup_20240101_000000.db",
            "size": "1.15 MB",
            "size_raw": 1205862,
            "created_at": "2024-01-01T00:00:00"
        }
    ]
    ```
    
    **注意**: 如果备份目录不存在，返回空数组。
    """
    if not os.path.exists(BACKUP_DIR):
        return []
        
    backups = []
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".db"):
            path = os.path.join(BACKUP_DIR, f)
            stat = os.stat(path)
            backups.append({
                "filename": f,
                "size": get_size(stat.st_size),
                "size_raw": stat.st_size,
                "created_at": datetime.datetime.fromtimestamp(stat.st_mtime)
            })
            
    # Sort by created_at desc
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups

@router.delete("/backups/{filename}")
async def delete_backup(filename: str):
    """
    删除指定的备份文件
    
    **参数**:
    - **filename**: 备份文件名（路径参数）
    
    **返回**:
    ```json
    {
        "message": "Backup deleted"
    }
    ```
    
    **错误响应**:
    - `404`: 备份文件不存在
    - `500`: 删除失败
    
    **安全措施**:
    - 仅允许删除备份目录中的文件
    - 文件名会被验证，防止路径穿透攻击
    """
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(path):
         raise HTTPException(status_code=404, detail="Backup file not found")
         
    try:
        os.remove(path)
        return {"message": "Backup deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backups/{filename}/download")
async def download_backup(filename: str):
    """
    下载备份文件
    
    **参数**:
    - **filename**: 备份文件名（路径参数）
    
    **返回**: 文件下载响应（FileResponse）
    
    **错误响应**:
    - `404`: 备份文件不存在
    
    **示例请求**:
    ```
    GET /api/system/backups/TaskManage_backup_20240101_120000.db/download
    ```
    
    **注意**: 浏览器会自动下载文件。
    """
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(path):
         raise HTTPException(status_code=404, detail="Backup file not found")
    return FileResponse(path, filename=filename)

@router.get("/data/overview")
async def get_data_overview(db: Session = Depends(get_db)):
    """
    获取数据概览
    
    返回系统中所有数据的概览信息，包括：
    - Python 版本/环境列表
    - 项目列表
    - 任务列表
    - 数据库路径和状态
    
    **返回**:
    ```json
    {
        "db_path": "/path/to/TaskManage.db",
        "db_exists": true,
        "python_versions": [
            {
                "id": 1,
                "name": "Python 3.12",
                "version": "3.12.9",
                "path": "/path/to/python",
                "status": "active",
                "is_conda": true,
                "path_exists": true
            }
        ],
        "python_environments": [...],
        "projects": [
            {
                "id": 1,
                "name": "MyProject",
                "path": "/path/to/project",
                "work_dir": "./",
                "output_dir": "/data/output",
                "path_exists": true
            }
        ],
        "tasks": [
            {
                "id": 1,
                "name": "MyTask",
                "status": "active",
                "project_id": 1,
                "env_id": 1,
                "trigger_type": "interval",
                "updated_at": "2024-01-01T12:00:00"
            }
        ]
    }
    ```
    
    **用途**: 用于系统管理页面展示所有数据的概览。
    """
    versions = db.query(env_models.PythonVersion).all()
    projects = db.query(project_models.Project).all()
    tasks = db.query(task_models.Task).all()

    versions_payload = []
    for v in versions:
        versions_payload.append({
            "id": v.id,
            "name": v.name,
            "version": v.version,
            "path": v.path,
            "status": v.status,
            "is_conda": v.is_conda,
            "path_exists": os.path.exists(v.path) if v.path else False
        })

    projects_payload = []
    for p in projects:
        projects_payload.append({
            "id": p.id,
            "name": p.name,
            "path": p.path,
            "work_dir": p.work_dir,
            "output_dir": p.output_dir,
            "path_exists": os.path.exists(p.path) if p.path else False
        })

    tasks_payload = []
    for t in tasks:
        tasks_payload.append({
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "project_id": t.project_id,
            "env_id": t.env_id,
            "trigger_type": t.trigger_type,
            "updated_at": t.updated_at
        })

    return {
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH),
        "python_versions": versions_payload,
        "python_environments": versions_payload,
        "projects": projects_payload,
        "tasks": tasks_payload
    }

@router.post("/data/clear")
async def clear_all_data():
    """
    清空所有数据（危险操作）
    
    **警告**: 此操作会删除所有数据，包括：
    - 所有任务（停止运行中的任务）
    - 所有项目文件
    - 所有环境目录
    - 所有任务日志和安装日志
    - 数据库中的所有记录
    
    **操作流程**:
    1. 停止所有运行中的任务
    2. 移除调度器中的所有任务
    3. 删除项目目录
    4. 删除环境目录
    5. 删除日志目录
    6. 清空数据库所有表
    
    **返回**:
    ```json
    {
        "message": "cleared",
        "removed_paths": {
            "projects": ["/path/to/project1", "/path/to/project2"],
            "envs": ["/path/to/env1"],
            "task_logs": ["/path/to/log1"],
            "install_logs": ["/path/to/install_log1"]
        }
    }
    ```
    
    **注意**: 
    - ⚠️ **此操作不可逆，请谨慎使用！**
    - 建议在执行前先创建备份
    - 主要用于开发和测试环境重置
    """
    try:
        if task_manager.scheduler and task_manager.scheduler.running:
            task_manager.scheduler.remove_all_jobs()
    except Exception:
        pass

    try:
        for execution_id in list(task_manager.running_processes.keys()):
            try:
                task_manager.stop_execution(execution_id)
            except Exception:
                pass
    except Exception:
        pass

    removed_paths = {}
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    removed_paths["projects"] = clear_directory(os.path.join(backend_dir, "projects"))
    removed_paths["envs"] = clear_directory(os.path.join(backend_dir, "envs"))
    removed_paths["task_logs"] = clear_directory(os.path.join(backend_dir, "logs", "tasks"))
    removed_paths["install_logs"] = clear_directory(os.path.join(backend_dir, "logs", "install"))

    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())

    return {
        "message": "cleared",
        "removed_paths": removed_paths
    }

@router.get("/stats")
async def get_system_stats():
    """
    获取系统资源统计信息
    
    返回系统的实时资源使用情况，包括 CPU、内存、磁盘和网络统计。
    
    **返回**:
    ```json
    {
        "cpu": {
            "percent": 25.5,
            "freq_current": "2400.00 MHz",
            "freq_min": "800.00 MHz",
            "freq_max": "3200.00 MHz",
            "cores": 4,
            "threads": 8,
            "per_cpu": [25.0, 26.0, 24.0, 27.0],
            "load_avg": [0.5, 0.6, 0.7]
        },
        "memory": {
            "total": "16.00 GB",
            "available": "8.00 GB",
            "used": "8.00 GB",
            "percent": 50.0,
            "buffers": "1.00 GB",
            "cached": "2.00 GB",
            "swap_total": "4.00 GB",
            "swap_used": "0.50 GB",
            "swap_percent": 12.5
        },
        "disk": {
            "partitions": [
                {
                    "device": "/dev/sda1",
                    "mountpoint": "/",
                    "fstype": "ext4",
                    "total": "500.00 GB",
                    "used": "250.00 GB",
                    "free": "250.00 GB",
                    "percent": 50.0
                }
            ],
            "read_count": 12345,
            "write_count": 6789,
            "read_bytes": "1.20 GB",
            "write_bytes": "500.00 MB"
        },
        "network": {
            "bytes_sent": "10.00 GB",
            "bytes_recv": "50.00 GB",
            "packets_sent": 1234567,
            "packets_recv": 2345678,
            "pids": 150
        }
    }
    ```
    
    **数据来源**: 使用 `psutil` 库获取系统资源信息
    
    **更新频率**: 实时数据，每次请求都会重新获取
    
    **跨平台支持**: 
    - Windows: 部分指标可能不可用（如 load_avg）
    - Linux/macOS: 完整支持所有指标
    """
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_freq = psutil.cpu_freq()
    cpu_cores = psutil.cpu_count(logical=False)
    cpu_threads = psutil.cpu_count(logical=True)
    per_cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
    
    # Memory
    svmem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Disk
    partitions = []
    try:
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": get_size(partition_usage.total),
                    "used": get_size(partition_usage.used),
                    "free": get_size(partition_usage.free),
                    "percent": partition_usage.percent
                })
            except PermissionError:
                continue
    except Exception:
        pass
            
    disk_io = psutil.disk_io_counters()
    
    # Network
    net_io = psutil.net_io_counters()
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "freq_current": f"{cpu_freq.current:.2f} MHz" if cpu_freq else "N/A",
            "freq_min": f"{cpu_freq.min:.2f} MHz" if cpu_freq else "N/A",
            "freq_max": f"{cpu_freq.max:.2f} MHz" if cpu_freq else "N/A",
            "cores": cpu_cores,
            "threads": cpu_threads,
            "per_cpu": per_cpu_percent,
            "load_avg": [x / cpu_cores for x in psutil.getloadavg()] if hasattr(psutil, "getloadavg") else [0, 0, 0] # Windows doesn't always have getloadavg
        },
        "memory": {
            "total": get_size(svmem.total),
            "available": get_size(svmem.available),
            "used": get_size(svmem.used),
            "percent": svmem.percent,
            "buffers": get_size(getattr(svmem, 'buffers', 0)),
            "cached": get_size(getattr(svmem, 'cached', 0)),
            "swap_total": get_size(swap.total),
            "swap_used": get_size(swap.used),
            "swap_percent": swap.percent
        },
        "disk": {
            "partitions": partitions,
            "read_count": disk_io.read_count if disk_io else 0,
            "write_count": disk_io.write_count if disk_io else 0,
            "read_bytes": get_size(disk_io.read_bytes) if disk_io else 0,
            "write_bytes": get_size(disk_io.write_bytes) if disk_io else 0,
        },
        "network": {
            "bytes_sent": get_size(net_io.bytes_sent),
            "bytes_recv": get_size(net_io.bytes_recv),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "pids": len(psutil.pids())
        }
    }
