from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import List
from core.database import get_db
from task_service import models, schemas
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
        task_manager.add_job(db_task)
    except Exception as e:
        print(f"Error scheduling task {db_task.id}: {e}")
        
    return db_task

@router.get("", response_model=List[schemas.Task])
async def list_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(models.Task).offset(skip).limit(limit).all()
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
            task_manager.update_job(db_task)
        else:
            task_manager.remove_job(db_task.id)
            
    return db_task

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
        attempt=1,
        node_id=os.environ.get("KUMO_NODE_ID", "master")
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
    background_tasks.add_task(run_task_execution, execution.id)
    
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
