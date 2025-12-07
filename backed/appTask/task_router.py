from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from appTask import models, schemas
from appTask.task_manager import task_manager, run_task_execution
import json
import datetime
import os

router = APIRouter()

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
            
    return tasks

@router.post("", response_model=schemas.Task)
async def create_task(task_in: schemas.TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = models.Task(**task_in.dict(), status="active") # Default to active
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Add to scheduler
    if task.trigger_type == 'immediate':
        background_tasks.add_task(run_task_execution, task.id)
    elif task.status == 'active':
        task_manager.add_job(task.id, task.trigger_type, task.trigger_value, task.status)
        
    return task

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task_in: schemas.TaskUpdate, db: Session = Depends(get_db)):
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
        task_manager.add_job(task.id, task.trigger_type, task.trigger_value, task.status)
    else:
        task_manager.remove_job(task.id)
        
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Remove from scheduler
    task_manager.remove_job(task.id)
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@router.post("/{task_id}/run")
async def run_task(task_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    background_tasks.add_task(run_task_execution, task_id)
    return {"message": "Task execution started"}

@router.post("/{task_id}/pause")
async def pause_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = "paused"
    db.commit()
    
    task_manager.pause_job(task.id)
    return {"message": "Task paused"}

@router.post("/{task_id}/resume")
async def resume_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = "active"
    db.commit()
    
    # Re-add job to be sure parameters are up to date and it's scheduled
    task_manager.add_job(task.id, task.trigger_type, task.trigger_value, task.status)
    return {"message": "Task resumed"}

@router.post("/executions/{execution_id}/stop")
async def stop_execution_endpoint(execution_id: int, db: Session = Depends(get_db)):
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
        return {"message": "Execution stopped"}
    else:
        # It might be running but we lost the handle (e.g. restart), or it just finished
        return {"message": "Could not stop execution (process might be gone)"}

@router.delete("/executions/{execution_id}")
async def delete_execution(execution_id: int, db: Session = Depends(get_db)):
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
            
    db.delete(execution)
    db.commit()
    return {"message": "Execution deleted"}

@router.get("/{task_id}/executions", response_model=List[schemas.TaskExecution])
async def list_executions(task_id: int, db: Session = Depends(get_db)):
    return db.query(models.TaskExecution).filter(models.TaskExecution.task_id == task_id).order_by(models.TaskExecution.start_time.desc()).limit(100).all()

@router.get("/executions/{execution_id}/log")
async def get_execution_log(execution_id: int, db: Session = Depends(get_db)):
    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    if not execution.log_file or not os.path.exists(execution.log_file):
         return {"log": execution.output or "No log file available."}
         
    try:
        with open(execution.log_file, "r", encoding="utf-8") as f:
            content = f.read()
        return {"log": content}
    except Exception as e:
        return {"log": f"Error reading log: {str(e)}"}
