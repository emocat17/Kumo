from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import List
from core.database import get_db
from task_service import models, schemas
from task_service.task_manager import task_manager, run_task_execution
from audit_service.service import create_audit_log
import json
import datetime
import os
import asyncio

router = APIRouter()

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    # 1. Task Counts
    total_tasks = db.query(models.Task).count()
    active_tasks = db.query(models.Task).filter(models.Task.status == 'active').count()
    
    # 2. Total Executions
    total_executions = db.query(models.TaskExecution).count()
    running_executions = db.query(models.TaskExecution).filter(models.TaskExecution.status == 'running').count()
    
    # 3. Success Rate (Last 7 Days)
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    recent_execs_query = db.query(models.TaskExecution).filter(models.TaskExecution.start_time >= seven_days_ago)
    
    total_recent = recent_execs_query.count()
    success_recent = recent_execs_query.filter(models.TaskExecution.status == 'success').count()
    
    success_rate_7d = 0.0
    if total_recent > 0:
        success_rate_7d = round((success_recent / total_recent) * 100, 2)
        
    # 4. Recent Executions (Limit 5)
    recent_executions = db.query(models.TaskExecution).order_by(models.TaskExecution.start_time.desc()).limit(5).all()
    
    # 5. Daily Stats (Last 7 Days)
    daily_stats = []
    for i in range(7):
        day = datetime.date.today() - datetime.timedelta(days=i)
        day_start = datetime.datetime.combine(day, datetime.time.min)
        day_end = datetime.datetime.combine(day, datetime.time.max)
        
        day_execs = db.query(models.TaskExecution).filter(
            models.TaskExecution.start_time >= day_start,
            models.TaskExecution.start_time <= day_end
        )
        
        success = day_execs.filter(models.TaskExecution.status == 'success').count()
        failed = day_execs.filter(models.TaskExecution.status == 'failed').count()
        
        daily_stats.append({
            "date": day.strftime("%Y-%m-%d"),
            "success": success,
            "failed": failed
        })
    
    daily_stats.reverse()
    
    # 6. Failure Stats (Top 5 Failed Tasks)
    failure_stats_query = db.query(
        models.TaskExecution.task_id,
        func.count(models.TaskExecution.id).label("failure_count")
    ).filter(models.TaskExecution.status == 'failed').group_by(models.TaskExecution.task_id).order_by(func.count(models.TaskExecution.id).desc()).limit(5).all()
    
    failure_stats = []
    for stat in failure_stats_query:
        task = db.query(models.Task).filter(models.Task.id == stat.task_id).first()
        task_name = task.name if task else f"Unknown Task ({stat.task_id})"
        failure_stats.append({
            "task_id": stat.task_id,
            "task_name": task_name,
            "failure_count": stat.failure_count
        })

    return {
        "total_tasks": total_tasks,
        "active_tasks": active_tasks,
        "running_executions": running_executions,
        "total_executions": total_executions,
        "success_rate_7d": success_rate_7d,
        "recent_executions": recent_executions,
        "daily_stats": daily_stats,
        "failure_stats": failure_stats
    }

@router.get("", response_model=List[schemas.Task])
async def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    # Populate next_run and execution info
    for task in tasks:
        next_run = task_manager.get_next_run_time(task.id)
        task.next_run = next_run
        
        # Get latest execution
        latest_exec = db.query(models.TaskExecution).filter(models.TaskExecution.task_id == task.id).order_by(models.TaskExecution.start_time.desc()).first()
        if latest_exec:
            task.last_execution_status = latest_exec.status
            task.latest_execution_id = latest_exec.id
            task.latest_execution_time = latest_exec.start_time
            
    return tasks

@router.post("", response_model=schemas.Task)
async def create_task(task_in: schemas.TaskCreate, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    task = models.Task(**task_in.dict(), status="active") # Default to active
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Add to scheduler
    if task.trigger_type == 'immediate':
        background_tasks.add_task(run_task_execution, task.id)
    elif task.status == 'active':
        task_manager.add_job(task.id, task.trigger_type, task.trigger_value, task.status, task.priority or 0)
    
    create_audit_log(
        db=db,
        operation_type="CREATE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Created task '{task.name}' with trigger {task.trigger_type}",
        operator_ip=request.client.host
    )
        
    return task

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task_in: schemas.TaskUpdate, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = task_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    db.commit()
    db.refresh(task)
    
    # Update scheduler
    # If status changed to paused, pause job
    # If status changed to active, add/resume job
    # If config changed, re-add job
    
    # Simple strategy: re-add job if active, remove if not
    if task.status == 'active':
        task_manager.add_job(task.id, task.trigger_type, task.trigger_value, task.status, task.priority or 0)
    else:
        task_manager.remove_job(task.id)

    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Updated task properties",
        operator_ip=request.client.host
    )
        
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Audit Log (before delete to capture name)
    create_audit_log(
        db=db,
        operation_type="DELETE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Deleted task '{task.name}'",
        operator_ip=request.client.host
    )

    # Remove from scheduler
    task_manager.remove_job(task.id)
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@router.post("/{task_id}/run")
async def run_task(task_id: int, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    background_tasks.add_task(run_task_execution, task_id)

    create_audit_log(
        db=db,
        operation_type="EXECUTE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Manually triggered execution for task '{task.name}'",
        operator_ip=request.client.host
    )

    return {"message": "Task execution started"}

@router.post("/{task_id}/pause")
async def pause_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = "paused"
    db.commit()
    
    task_manager.pause_job(task.id)

    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Paused task '{task.name}'",
        operator_ip=request.client.host
    )

    return {"message": "Task paused"}

@router.post("/{task_id}/resume")
async def resume_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = "active"
    db.commit()
    
    # Re-add job to be sure parameters are up to date and it's scheduled
    task_manager.add_job(task.id, task.trigger_type, task.trigger_value, task.status, task.priority or 0)

    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="TASK",
        target_id=str(task.id),
        target_name=task.name,
        details=f"Resumed task '{task.name}'",
        operator_ip=request.client.host
    )

    return {"message": "Task resumed"}

@router.post("/executions/{execution_id}/stop")
async def stop_execution_endpoint(execution_id: int, request: Request, db: Session = Depends(get_db)):
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status != 'running':
        return {"message": "Execution is not running"}
        
    success = task_manager.stop_execution(execution_id)
    if success:
        execution.status = "stopped"
        execution.end_time = datetime.datetime.now()
        execution.output = (execution.output or "") + "\n[Process stopped by user]"
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
            for i, line in enumerate(f):
                if q.lower() in line.lower():
                    results.append({
                        "line": i + 1,
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
