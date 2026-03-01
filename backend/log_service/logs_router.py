from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from core.database import get_db
from core.logging import get_logger
from task_service import models as task_models
import os
import datetime
import shutil

router = APIRouter()
logger = get_logger(__name__)

# Use relative path to ensure we find the logs regardless of CWD
# .../backend/log_service/logs_router.py -> .../backend/logs/tasks
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BACKEND_DIR, "logs", "tasks")

def get_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    return LOG_DIR

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

@router.get("")
async def list_logs(
    db: Session = Depends(get_db),
    project_id: int = Query(None, description="Filter by project ID")
):
    log_dir = get_log_dir()
    files = []
    
    # Pre-fetch all tasks to map ID to Name and Project
    tasks_query = db.query(task_models.Task)
    if project_id:
        tasks_query = tasks_query.filter(task_models.Task.project_id == project_id)
        
    tasks = tasks_query.all()
    # Map task_id -> task_name (and effectively serves as a set of allowed task_ids if filtered)
    task_map = {t.id: t.name for t in tasks}
    allowed_task_ids = set(task_map.keys()) if project_id else None
    
    if os.path.exists(log_dir):
        for f in os.listdir(log_dir):
            if f.endswith(".log"):
                # Parse filename: task_{task_id}_exec_{exec_id}.log
                try:
                    parts = f.split('_')
                    if len(parts) >= 2 and parts[0] == 'task':
                        task_id = int(parts[1])
                        
                        # Filter by project
                        if project_id and task_id not in allowed_task_ids:
                            continue
                            
                        task_name = task_map.get(task_id, f"Task {task_id}")
                    else:
                        if project_id: continue # Skip unknown files when filtering
                        task_name = "Unknown Task"
                except Exception:
                    if project_id: continue
                    task_name = "Unknown Task"

                path = os.path.join(log_dir, f)
                stat = os.stat(path)
                
                files.append({
                    "filename": f,
                    "task_name": task_name,
                    "size": format_size(stat.st_size),
                    "size_raw": stat.st_size,
                    "created_at": datetime.datetime.fromtimestamp(stat.st_mtime),
                    "path": path
                })
    
    # Sort by created_at desc
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return files

@router.get("/{filename}/download")
async def download_log(filename: str):
    log_dir = get_log_dir()
    path = os.path.join(log_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Log file not found")
    return FileResponse(path, filename=filename)

from pydantic import BaseModel
from typing import List

class BatchDeleteRequest(BaseModel):
    filenames: List[str]

@router.get("/{filename}/content")
async def get_log_content(filename: str, tail_kb: int = Query(None, description="Read last N KB")):
    log_dir = get_log_dir()
    path = os.path.join(log_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Log file not found")
    try:
        file_size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            if tail_kb:
                bytes_to_read = tail_kb * 1024
                if file_size > bytes_to_read:
                    f.seek(file_size - bytes_to_read)
                    # Discard partial line
                    f.readline()
                    content = f.read()
                    content = f"[Log truncated. Showing last {tail_kb}KB. Download for full log.]\n" + content
                else:
                    content = f.read()
            else:
                content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{filename}/search")
async def search_log(filename: str, q: str = Query(..., description="Keyword to search"), limit: int = 1000):
    """
    Search for a keyword in the log file (case-insensitive).
    Returns matching lines with line numbers.
    """
    log_dir = get_log_dir()
    path = os.path.join(log_dir, filename)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Log file not found")
        
    if not q:
        return {"matches": []}
        
    matches = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if q.lower() in line.lower():
                    matches.append({
                        "line": i,
                        "content": line.strip()
                    })
                    if len(matches) >= limit:
                        break
        return {"matches": matches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-delete")
async def batch_delete_logs(request: BatchDeleteRequest):
    log_dir = get_log_dir()
    deleted_count = 0
    errors = []
    
    for filename in request.filenames:
        path = os.path.join(log_dir, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted_count += 1
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
                
    return {"message": f"Deleted {deleted_count} logs", "errors": errors}

@router.delete("/{filename}")
async def delete_log(filename: str):
    log_dir = get_log_dir()
    path = os.path.join(log_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Log file not found")
    try:
        os.remove(path)
        return {"message": "Log deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_logs(days: int = Query(..., description="Delete logs older than these days"), delete_all: bool = False):
    log_dir = get_log_dir()
    count = 0
    now = datetime.datetime.now().timestamp()
    
    if not os.path.exists(log_dir):
        return {"message": "No logs directory"}

    for f in os.listdir(log_dir):
        if f.endswith(".log"):
            path = os.path.join(log_dir, f)
            try:
                if delete_all:
                    os.remove(path)
                    count += 1
                else:
                    stat = os.stat(path)
                    # mtime is modification time, which is close enough to "last active"
                    if now - stat.st_mtime > days * 86400:
                        os.remove(path)
                        count += 1
            except Exception as e:
                logger.error(f"Error deleting {f}: {e}")
                
    return {"message": f"Deleted {count} log files"}
