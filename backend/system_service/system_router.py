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
    """Get all system configurations"""
    return db.query(system_models.SystemConfig).all()

@router.post("/config", response_model=system_schemas.SystemConfig)
async def create_or_update_config(config: system_schemas.SystemConfigCreate, db: Session = Depends(get_db)):
    """Create or update a system configuration"""
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
    """Get a specific configuration by key"""
    config = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

# --- System Info Endpoints ---

@router.get("/info")
async def get_system_info(db: Session = Depends(get_db)):
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
    """Create a manual backup of the database"""
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
    """List all available backups"""
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
    """Delete a specific backup"""
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
    """Download a backup file"""
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(path):
         raise HTTPException(status_code=404, detail="Backup file not found")
    return FileResponse(path, filename=filename)

@router.get("/data/overview")
async def get_data_overview(db: Session = Depends(get_db)):
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
