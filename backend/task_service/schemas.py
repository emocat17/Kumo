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
    retry_count: Optional[int] = 0
    retry_delay: Optional[int] = 60
    timeout: Optional[int] = 3600
    priority: Optional[int] = 0

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
    retry_count: Optional[int] = None
    retry_delay: Optional[int] = None
    timeout: Optional[int] = None
    priority: Optional[int] = None

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
    attempt: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output: Optional[str] = None
    max_cpu_percent: Optional[float] = None
    max_memory_mb: Optional[float] = None

class TaskExecution(TaskExecutionBase):
    id: int
    task_id: int
    log_file: Optional[str] = None

    class Config:
        from_attributes = True

class OutputTypeStat(BaseModel):
    ext: str
    count: int

class OutputSample(BaseModel):
    name: str
    path: str
    size: int
    mtime: datetime

class OutputStats(BaseModel):
    total_files: int
    total_bytes: int
    recent_files: int
    recent_bytes: int
    types: List[OutputTypeStat]
    scanned_files: int
    truncated: bool

class ExecutionWindowStats(BaseModel):
    started: int
    finished: int
    success: int
    failed: int
    running: int

class LatestExecutionStat(BaseModel):
    task_id: int
    task_name: str
    execution_id: Optional[int] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    max_memory_mb: Optional[float] = None
    log_file: Optional[str] = None

class TimeSeriesPoint(BaseModel):
    label: str
    value: float

class TimeSeriesGroup(BaseModel):
    duration: List[TimeSeriesPoint]
    max_cpu: List[TimeSeriesPoint]
    max_memory: List[TimeSeriesPoint]

class TestMetricsEvidence(BaseModel):
    output_samples: List[OutputSample]
    log_files: List[LatestExecutionStat]

class TestMetricsOverview(BaseModel):
    project_id: int
    project_name: str
    output_dir: str
    task_count: int
    window_seconds: int
    output: OutputStats
    executions_window: ExecutionWindowStats
    latest_executions: List[LatestExecutionStat]
    timeseries: TimeSeriesGroup
    evidence: TestMetricsEvidence


class DailyStats(BaseModel):
    date: str
    success: int
    failed: int

class FailureStat(BaseModel):
    task_id: int
    task_name: str
    failure_count: int

class DashboardStats(BaseModel):
    total_tasks: int
    active_tasks: int
    running_executions: int
    total_executions: int
    success_rate_7d: float
    recent_executions: List[TaskExecution]
    daily_stats: List[DailyStats]
    failure_stats: List[FailureStat]

class CronPreviewRequest(BaseModel):
    cron_expression: str

class CronPreviewResponse(BaseModel):
    next_run_times: List[str]
