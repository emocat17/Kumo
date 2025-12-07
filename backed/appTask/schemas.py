from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import json

class TaskBase(BaseModel):
    name: str
    command: str
    project_id: int
    env_id: Optional[int] = None
    trigger_type: str
    trigger_value: str # JSON string or plain string
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    command: Optional[str] = None
    project_id: Optional[int] = None
    env_id: Optional[int] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

class Task(TaskBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    node_id: Optional[str] = None
    next_run: Optional[datetime] = None # Calculated field
    last_execution_status: Optional[str] = None
    latest_execution_id: Optional[int] = None
    latest_execution_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskExecutionBase(BaseModel):
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output: Optional[str] = None

class TaskExecution(TaskExecutionBase):
    id: int
    task_id: int
    log_file: Optional[str] = None

    class Config:
        from_attributes = True
