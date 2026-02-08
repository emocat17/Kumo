from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import List
from core.database import get_db
from task_service import models, schemas
from project_service import models as project_models
from task_service.task_manager import task_manager, run_task_execution
from audit_service.service import create_audit_log
from apscheduler.triggers.cron import CronTrigger
import json
import datetime
import os
import asyncio

router = APIRouter()

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    project_id: int = Query(None, description="Filter by project ID")
):
    # Base filters
    task_filter = []
    if project_id:
        task_filter.append(models.Task.project_id == project_id)

    # 1. Task Counts
    total_tasks = db.query(models.Task).filter(*task_filter).count()
    active_tasks = db.query(models.Task).filter(models.Task.status == 'active', *task_filter).count()
    
    # 2. Total Executions
    exec_query = db.query(models.TaskExecution)
    if project_id:
        exec_query = exec_query.join(models.Task).filter(models.Task.project_id == project_id)
        
    total_executions = exec_query.count()
    running_executions = exec_query.filter(models.TaskExecution.status == 'running').count()
    
    # 3. Success Rate (Last 7 Days)
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    recent_execs_query = exec_query.filter(models.TaskExecution.start_time >= seven_days_ago)
    
    total_recent = recent_execs_query.count()
    success_recent = recent_execs_query.filter(models.TaskExecution.status == 'success').count()
    
    success_rate_7d = 0.0
    if total_recent > 0:
        success_rate_7d = round((success_recent / total_recent) * 100, 2)
        
    # 4. Recent Executions (Limit 5)
    recent_executions = exec_query.order_by(models.TaskExecution.start_time.desc()).limit(5).all()
    
    # 5. Daily Stats (Last 14 days)
    # We will fetch this in a separate call or here? 
    # The Schema expects daily_stats, failure_stats.
    # Let's add them here to match schema.
    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)
    
    date_col = func.date(models.TaskExecution.start_time)
    
    daily_results = db.query(
        date_col.label("date"),
        models.TaskExecution.status,
        func.count(models.TaskExecution.id).label("count")
    ).filter(
        models.TaskExecution.start_time >= start_date
    )
    if project_id:
        daily_results = daily_results.join(models.Task).filter(models.Task.project_id == project_id)
        
    daily_results = daily_results.group_by(
        date_col,
        models.TaskExecution.status
    ).all()
    
    stats_map = {}
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        stats_map[date_str] = {"success": 0, "failed": 0}
        current += datetime.timedelta(days=1)
        
    for r in daily_results:
        date_str = r.date
        status = r.status
        count = r.count
        if date_str in stats_map:
            if status == "success":
                stats_map[date_str]["success"] += count
            elif status == "failed":
                stats_map[date_str]["failed"] += count
                
    daily_stats_list = []
    for d in sorted(stats_map.keys()):
        daily_stats_list.append(schemas.DailyStats(
            date=d,
            success=stats_map[d]["success"],
            failed=stats_map[d]["failed"]
        ))
        
    # 6. Failure Stats (Top 5)
    fail_query = db.query(
        models.TaskExecution.task_id,
        models.Task.name.label("task_name"),
        func.count(models.TaskExecution.id).label("failure_count")
    ).join(models.Task).filter(
        models.TaskExecution.status == 'failed'
    )
    if project_id:
        fail_query = fail_query.filter(models.Task.project_id == project_id)
        
    fail_results = fail_query.group_by(
        models.TaskExecution.task_id,
        models.Task.name
    ).order_by(func.count(models.TaskExecution.id).desc()).limit(5).all()
    
    failure_stats_list = [
        schemas.FailureStat(task_id=r.task_id, task_name=r.task_name, failure_count=r.failure_count)
        for r in fail_results
    ]

    return schemas.DashboardStats(
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        running_executions=running_executions,
        total_executions=total_executions,
        success_rate_7d=success_rate_7d,
        recent_executions=recent_executions,
        daily_stats=daily_stats_list,
        failure_stats=failure_stats_list
    )

@router.post("", response_model=schemas.Task)
async def create_task(task: schemas.TaskCreate, request: Request, db: Session = Depends(get_db)):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="CREATE",
        target_type="TASK",
        target_id=str(db_task.id),
        target_name=db_task.name,
        details=f"Created task '{db_task.name}' with command '{db_task.command}'",
        operator_ip=request.client.host
    )
    
    # Schedule task
    try:
        task_manager.add_job(
            db_task.id,
            db_task.trigger_type,
            db_task.trigger_value,
            db_task.status,
            db_task.priority or 0
        )
    except Exception as e:
        print(f"Error scheduling task {db_task.id}: {e}")
        
    return db_task

@router.get("", response_model=List[schemas.Task])
async def list_tasks(skip: int = 0, limit: int = 100, project_id: int = None, db: Session = Depends(get_db)):
    query = db.query(models.Task)
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    tasks = query.offset(skip).limit(limit).all()
    # Update runtime status
    for t in tasks:
        t.next_run = task_manager.get_next_run_time(t.id)
        # Get latest execution info
        latest_exec = db.query(models.TaskExecution).filter(
            models.TaskExecution.task_id == t.id
        ).order_by(models.TaskExecution.start_time.desc()).first()
        
        if latest_exec:
            t.last_execution_status = latest_exec.status
            t.latest_execution_id = latest_exec.id
            t.latest_execution_time = latest_exec.start_time
            
    return tasks

def resolve_output_dir(project: project_models.Project):
    if project.output_dir:
        return project.output_dir
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(backend_dir)
    return os.path.join(root_dir, "Data")

def parse_task_ids(task_ids: str):
    if not task_ids:
        return []
    parts = [p.strip() for p in task_ids.split(",")]
    return [int(p) for p in parts if p.isdigit()]

@router.get("/test-metrics/overview", response_model=schemas.TestMetricsOverview)
async def get_test_metrics_overview(project_id: int, task_ids: str = None, window_seconds: int = 10, sample_limit: int = 50, db: Session = Depends(get_db)):
    project = db.query(project_models.Project).filter(project_models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ids = parse_task_ids(task_ids)
    task_query = db.query(models.Task).filter(models.Task.project_id == project_id)
    if ids:
        task_query = task_query.filter(models.Task.id.in_(ids))
    tasks = task_query.all()

    output_dir = resolve_output_dir(project)
    now_ts = datetime.datetime.now().timestamp()
    max_scan = 20000
    scanned = 0
    truncated = False
    total_files = 0
    total_bytes = 0
    recent_files = 0
    recent_bytes = 0
    type_map = {}
    samples = []

    if output_dir and os.path.exists(output_dir):
        for root, _, files in os.walk(output_dir):
            for filename in files:
                if scanned >= max_scan:
                    truncated = True
                    break
                scanned += 1
                full_path = os.path.join(root, filename)
                try:
                    stat = os.stat(full_path)
                except Exception:
                    continue
                total_files += 1
                total_bytes += stat.st_size
                ext = os.path.splitext(filename)[1].lower() or "no_ext"
                type_map[ext] = type_map.get(ext, 0) + 1
                if now_ts - stat.st_mtime <= window_seconds:
                    recent_files += 1
                    recent_bytes += stat.st_size
                samples.append({
                    "name": filename,
                    "path": full_path,
                    "size": stat.st_size,
                    "mtime": datetime.datetime.fromtimestamp(stat.st_mtime)
                })
            if truncated:
                break

    samples.sort(key=lambda x: x["mtime"], reverse=True)
    output_samples = samples[:sample_limit]
    types = [{"ext": k, "count": v} for k, v in sorted(type_map.items(), key=lambda x: x[1], reverse=True)]

    task_ids_list = [t.id for t in tasks]
    exec_query = db.query(models.TaskExecution).join(models.Task).filter(models.Task.project_id == project_id)
    if task_ids_list:
        exec_query = exec_query.filter(models.TaskExecution.task_id.in_(task_ids_list))

    start_window = datetime.datetime.now() - datetime.timedelta(seconds=window_seconds)
    started = exec_query.filter(models.TaskExecution.start_time >= start_window).count()
    finished = exec_query.filter(models.TaskExecution.end_time != None, models.TaskExecution.end_time >= start_window).count()
    success = exec_query.filter(models.TaskExecution.status == "success", models.TaskExecution.start_time >= start_window).count()
    failed = exec_query.filter(models.TaskExecution.status == "failed", models.TaskExecution.start_time >= start_window).count()
    running = exec_query.filter(models.TaskExecution.status == "running").count()

    latest_executions = []
    log_files = []
    for t in tasks:
        latest = db.query(models.TaskExecution).filter(models.TaskExecution.task_id == t.id).order_by(models.TaskExecution.start_time.desc()).first()
        if latest:
            item = {
                "task_id": t.id,
                "task_name": t.name,
                "execution_id": latest.id,
                "status": latest.status,
                "start_time": latest.start_time,
                "end_time": latest.end_time,
                "duration": latest.duration,
                "max_cpu_percent": latest.max_cpu_percent,
                "max_memory_mb": latest.max_memory_mb,
                "log_file": latest.log_file
            }
        else:
            item = {
                "task_id": t.id,
                "task_name": t.name
            }
        latest_executions.append(item)
        log_files.append(item)

    series_limit = 30
    series_execs = exec_query.order_by(models.TaskExecution.start_time.desc()).limit(series_limit).all()
    duration_series = []
    cpu_series = []
    mem_series = []
    for e in reversed(series_execs):
        label = e.start_time.strftime("%m-%d %H:%M:%S") if e.start_time else str(e.id)
        duration_series.append({"label": label, "value": float(e.duration or 0)})
        cpu_series.append({"label": label, "value": float(e.max_cpu_percent or 0)})
        mem_series.append({"label": label, "value": float(e.max_memory_mb or 0)})

    return {
        "project_id": project.id,
        "project_name": project.name,
        "output_dir": output_dir,
        "task_count": len(tasks),
        "window_seconds": window_seconds,
        "output": {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "recent_files": recent_files,
            "recent_bytes": recent_bytes,
            "types": types,
            "scanned_files": scanned,
            "truncated": truncated
        },
        "executions_window": {
            "started": started,
            "finished": finished,
            "success": success,
            "failed": failed,
            "running": running
        },
        "latest_executions": latest_executions,
        "timeseries": {
            "duration": duration_series,
            "max_cpu": cpu_series,
            "max_memory": mem_series
        },
        "evidence": {
            "output_samples": output_samples,
            "log_files": log_files
        }
    }

@router.get("/{task_id}", response_model=schemas.Task)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.next_run = task_manager.get_next_run_time(task.id)
    return task

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task_update: schemas.TaskUpdate, request: Request, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = task_update.model_dump(exclude_unset=True)
    
    # Check if critical fields changed
    reschedule_needed = False
    critical_fields = ['trigger_type', 'trigger_value', 'command', 'env_id', 'project_id', 'status', 'timeout', 'retry_count', 'retry_delay']
    if any(k in update_data for k in critical_fields):
        reschedule_needed = True
        
    for key, value in update_data.items():
        setattr(db_task, key, value)
        
    db.commit()
    db.refresh(db_task)
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="TASK",
        target_id=str(db_task.id),
        target_name=db_task.name,
        details=f"Updated task '{db_task.name}'. Fields: {', '.join(update_data.keys())}",
        operator_ip=request.client.host
    )
    
    if reschedule_needed:
        if db_task.status == 'active':
            task_manager.add_job(
                db_task.id,
                db_task.trigger_type,
                db_task.trigger_value,
                db_task.status,
                db_task.priority or 0
            )
        else:
            task_manager.remove_job(db_task.id)
            
    return db_task

@router.post("/{task_id}/pause")
async def pause_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = 'paused'
    db.commit()
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="PAUSE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Paused task '{task.name}'",
        operator_ip=request.client.host
    )
    
    task_manager.pause_job(task_id)
    return {"message": "Task paused"}

@router.post("/{task_id}/resume")
async def resume_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = 'active'
    db.commit()
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="RESUME",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Resumed task '{task.name}'",
        operator_ip=request.client.host
    )
    
    # Check if job exists (if it was removed due to update or not loaded)
    # Since we can't easily check scheduler job existence from here without accessing private method or catching exception,
    # and add_job handles replacement, we can just call add_job to be safe.
    # But resume_job is more efficient if it exists.
    # task_manager.scheduler.get_job(str(task_id)) is available if we import task_manager
    
    if task_manager.scheduler.get_job(str(task_id)):
        task_manager.resume_job(task_id)
    else:
        task_manager.add_job(
            task.id,
            task.trigger_type,
            task.trigger_value,
            task.status,
            task.priority or 0
        )
         
    return {"message": "Task resumed"}

@router.delete("/{task_id}")
async def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Remove from scheduler
    task_manager.remove_job(task_id)
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="DELETE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Deleted task '{task.name}'",
        operator_ip=request.client.host
    )
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@router.post("/{task_id}/run")
async def run_task(task_id: int, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Create execution record immediately
    execution = models.TaskExecution(
        task_id=task.id,
        status='pending',
        start_time=datetime.datetime.now(),
        attempt=1
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="RUN",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Manually triggered task '{task.name}' (Exec ID: {execution.id})",
        operator_ip=request.client.host
    )
    
    # Run in background
    background_tasks.add_task(run_task_execution, task.id, 1, execution.id)
    
    return {"message": "Task started", "execution_id": execution.id}

@router.post("/executions/{execution_id}/stop")
async def stop_execution(execution_id: int, request: Request, db: Session = Depends(get_db)):
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if execution.status == 'running' or execution.status == 'pending':
        stopped = task_manager.stop_execution(execution_id)
        
        # Update DB status if not already updated by the process
        if execution.status != 'stopped' and execution.status != 'failed' and execution.status != 'success':
             execution.status = 'stopped'
             execution.end_time = datetime.datetime.now()
             execution.output = (execution.output or "") + "\n[System] Execution stopped by user."
             db.commit()
        
        # Audit Log
        task = db.query(models.Task).filter(models.Task.id == execution.task_id).first()
        task_name = task.name if task else "Unknown Task"
        
        create_audit_log(
            db=db,
            operation_type="STOP",
            target_type="TASK",
            target_id=str(execution.task_id),
            target_name=task_name,
            details=f"Stopped execution {execution_id} for task '{task_name}'",
            operator_ip=request.client.host
        )
        
        return {"message": "Execution stopped"}
    else:
        # It might be running but we lost the handle (e.g. restart), or it just finished
        return {"message": "Could not stop execution (process might be gone)"}

@router.delete("/executions/{execution_id}")
async def delete_execution(execution_id: int, request: Request, db: Session = Depends(get_db)):
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # If running, try stop first
    if execution.status == 'running':
        task_manager.stop_execution(execution_id)
        
    # Delete log file
    if execution.log_file and os.path.exists(execution.log_file):
        try:
            os.remove(execution.log_file)
        except:
            pass
            
    # Audit Log
    task = db.query(models.Task).filter(models.Task.id == execution.task_id).first()
    task_name = task.name if task else "Unknown Task"
    
    create_audit_log(
        db=db,
        operation_type="DELETE",
        target_type="EXECUTION",
        target_id=str(execution.id),
        target_name=f"Exec {execution.id} ({task_name})",
        details=f"Deleted execution {execution.id} for task '{task_name}'",
        operator_ip=request.client.host
    )

    db.delete(execution)
    db.commit()
    return {"message": "Execution deleted"}

@router.get("/{task_id}/executions", response_model=List[schemas.TaskExecution])
async def list_executions(task_id: int, db: Session = Depends(get_db)):
    return db.query(models.TaskExecution).filter(models.TaskExecution.task_id == task_id).order_by(models.TaskExecution.start_time.desc()).limit(100).all()

@router.get("/executions/{execution_id}/log")
async def get_execution_log(execution_id: int, tail_kb: int = Query(None), db: Session = Depends(get_db)):
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if not execution.log_file or not os.path.exists(execution.log_file):
         return {"log": execution.output or "No log file available."}
         
    try:
        file_size = os.path.getsize(execution.log_file)
        with open(execution.log_file, "r", encoding="utf-8", errors="ignore") as f:
            if tail_kb:
                bytes_to_read = tail_kb * 1024
                if file_size > bytes_to_read:
                    f.seek(file_size - bytes_to_read)
                    f.readline()
                    content = f.read()
                    content = f"[Log truncated. Showing last {tail_kb}KB. Download for full log.]\n" + content
                else:
                    content = f.read()
            else:
                content = f.read()
        return {"log": content}
    except Exception as e:
        return {"log": f"Error reading log: {str(e)}"}

@router.get("/executions/{execution_id}/log/search")
async def search_execution_log(execution_id: int, q: str = Query(..., min_length=1), limit: int = 100, db: Session = Depends(get_db)):
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if not execution.log_file or not os.path.exists(execution.log_file):
         return {"results": []}
         
    results = []
    try:
        with open(execution.log_file, "r", encoding="utf-8", errors="ignore") as f:
            line_num = 0
            for line in f:
                line_num += 1
                if q.lower() in line.lower():
                    results.append({
                        "line": line_num,
                        "content": line.strip()
                    })
                    if len(results) >= limit:
                        break
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/logs/{execution_id}")
async def websocket_log(websocket: WebSocket, execution_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution or not execution.log_file:
        await websocket.send_text("Log file not found or execution does not exist.")
        await websocket.close()
        return

    log_path = execution.log_file
    
    # Wait for file to be created if it doesn't exist yet (e.g. just started)
    retries = 0
    while not os.path.exists(log_path) and retries < 20:
        await asyncio.sleep(0.1)
        retries += 1
        
    if not os.path.exists(log_path):
        await websocket.send_text("Log file creation timed out.")
        await websocket.close()
        return

    try:
        file_size = os.path.getsize(log_path)
        TAIL_BYTES = 50 * 1024 # 50KB

        with open(log_path, "r", encoding="utf-8", errors='replace') as f:
            # Send initial content
            if file_size > TAIL_BYTES:
                f.seek(file_size - TAIL_BYTES)
                f.readline()
                await websocket.send_text(f"[Log truncated. Showing last {TAIL_BYTES/1024}KB...]\n")
                content = f.read()
                if content:
                    await websocket.send_text(content)
            else:
                content = f.read()
                if content:
                    await websocket.send_text(content)
            
            # Tail the file
            while True:
                # Check if client disconnected
                # (WebSocket.receive_text() would raise, but we are in a send loop)
                # We assume client is connected if no exception.
                
                line = f.read()
                if line:
                    await websocket.send_text(line)
                else:
                    # Check if execution finished
                    # We need to refresh execution status from DB, but doing it in loop is expensive.
                    # Instead, we can check if process is still in task_manager.running_processes
                    # But task_manager might be in another worker if we were using uvicorn workers (but we are likely single process here)
                    # Or we just check if file is still being written to?
                    # Simplest: Just sleep. If the task is done, eventually the user will disconnect or we can implement a "done" signal.
                    # Let's check DB every 2 seconds maybe?
                    await asyncio.sleep(0.05) # 50ms latency
                    
    except WebSocketDisconnect:
        print(f"Client disconnected from log {execution_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except:
            pass

@router.get("/stats/daily")
async def get_daily_task_stats(days: int = 14, db: Session = Depends(get_db)):
    """
    Get task execution statistics for the last N days.
    Returns counts of success and failed tasks grouped by date.
    """
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    
    # Query for daily counts grouped by date and status
    # SQLAlchemy logic for SQLite date grouping
    date_col = func.date(models.TaskExecution.start_time)
    
    results = db.query(
        date_col.label("date"),
        models.TaskExecution.status,
        func.count(models.TaskExecution.id).label("count")
    ).filter(
        models.TaskExecution.start_time >= start_date
    ).group_by(
        date_col,
        models.TaskExecution.status
    ).all()
    
    # Process results into a structured format
    # { "2023-10-01": { "success": 5, "failed": 1 }, ... }
    stats_map = {}
    
    # Initialize all dates in range with 0
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        stats_map[date_str] = {"success": 0, "failed": 0}
        current += datetime.timedelta(days=1)
        
    for r in results:
        date_str = r.date
        status = r.status
        count = r.count
        
        if date_str in stats_map:
            if status == "success":
                stats_map[date_str]["success"] += count
            elif status == "failed":
                stats_map[date_str]["failed"] += count
            
    # Convert to list for frontend chart
    dates = sorted(stats_map.keys())
    success_data = [stats_map[d]["success"] for d in dates]
    failed_data = [stats_map[d]["failed"] for d in dates]
    
    return {
        "dates": dates,
        "success": success_data,
        "failed": failed_data
    }

@router.post("/cron/preview", response_model=schemas.CronPreviewResponse)
async def preview_cron(request: schemas.CronPreviewRequest):
    try:
        trigger = CronTrigger.from_crontab(request.cron_expression)
        now = datetime.datetime.now()
        next_times = []
        next_run = now
        for _ in range(5):
            next_run = trigger.get_next_fire_time(None, next_run)
            if next_run:
                next_times.append(next_run.strftime("%Y-%m-%d %H:%M:%S"))
                # Advance slightly to find the next one
                next_run = next_run + datetime.timedelta(seconds=1)
            else:
                break
        return {"next_run_times": next_times}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid cron expression: {str(e)}")
