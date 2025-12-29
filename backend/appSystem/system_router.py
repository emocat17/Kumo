import platform
import time
import psutil
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from appEnv import models as env_models
from appProject import models as project_models
from appSystem import models as system_models
from appSystem import schemas as system_schemas

router = APIRouter()

# Record application start time
APP_START_TIME = time.time()

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
