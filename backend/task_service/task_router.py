from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, desc, select
from typing import List
from core.database import get_db
from core.logging import get_logger
from core.cache import query_cache
from task_service import models, schemas
from project_service import models as project_models
from task_service.task_manager import task_manager
from task_service.task_executor import run_task_execution
from audit_service.service import create_audit_log
from apscheduler.triggers.cron import CronTrigger
import json
import csv
import io
import datetime
import os
import asyncio

router = APIRouter()
logger = get_logger(__name__)

@router.get("/dashboard/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    project_id: int = Query(None, description="Filter by project ID")
):
    """
    获取任务仪表板统计数据
    
    - **project_id**: 可选，按项目 ID 过滤统计信息
    
    返回包括：
    - 任务总数和活跃任务数
    - 执行总数和正在运行的任务数
    - 最近7天的成功率
    - 最近5次执行记录
    - 最近14天的每日统计
    - 失败次数最多的前5个任务
    """
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
        # Handle both string and date object from SQLite
        if hasattr(r.date, 'strftime'):
            date_str = r.date.strftime("%Y-%m-%d")
        else:
            date_str = str(r.date)
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
    """
    创建新任务
    
    - **name**: 任务名称
    - **command**: 执行命令
    - **project_id**: 关联的项目 ID
    - **trigger_type**: 触发器类型（interval/cron/date/immediate）
    - **trigger_value**: 触发器配置（JSON 字符串）
    - **env_id**: 可选，Python 环境 ID
    - **retry_count**: 重试次数
    - **retry_delay**: 重试延迟（秒）
    - **timeout**: 超时时间（秒）
    - **priority**: 优先级
    
    创建后会自动添加到调度器中（如果状态为 active）
    """
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
        logger.error(f"Error scheduling task {db_task.id}: {e}")
        
    return db_task

@router.get("", response_model=List[schemas.Task])
async def list_tasks(skip: int = 0, limit: int = 100, project_id: int = None, db: Session = Depends(get_db)):
    """
    获取任务列表
    
    - **skip**: 跳过的记录数（分页）
    - **limit**: 返回的最大记录数（默认100）
    - **project_id**: 可选，按项目 ID 过滤
    
    返回的任务包含运行时信息：
    - next_run: 下次运行时间
    - last_execution_status: 最后一次执行状态
    - latest_execution_id: 最新执行 ID
    - latest_execution_time: 最新执行时间
    """
    # 构建缓存键
    cache_key = f"tasks_list_{skip}_{limit}_{project_id}"
    
    # 尝试从缓存获取
    cached_result = query_cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    query = db.query(models.Task)
    if project_id:
        query = query.filter(models.Task.project_id == project_id)
    tasks = query.offset(skip).limit(limit).all()
    
    if not tasks:
        return tasks
    
    # 批量查询最新执行记录，避免 N+1 查询问题
    task_ids = [t.id for t in tasks]
    
    # 使用子查询获取每个任务的最新执行记录
    subquery = select(
        models.TaskExecution.task_id,
        models.TaskExecution.id.label('exec_id'),
        models.TaskExecution.status.label('exec_status'),
        models.TaskExecution.start_time.label('exec_start_time'),
        func.row_number().over(
            partition_by=models.TaskExecution.task_id,
            order_by=desc(models.TaskExecution.start_time)
        ).label('rn')
    ).where(models.TaskExecution.task_id.in_(task_ids)).subquery()
    
    latest_executions = db.query(subquery).filter(subquery.c.rn == 1).all()
    
    # 构建执行记录映射
    exec_map = {row.task_id: {
        'id': row.exec_id,
        'status': row.exec_status,
        'start_time': row.exec_start_time
    } for row in latest_executions}
    
    # 更新任务运行时信息
    for t in tasks:
        t.next_run = task_manager.get_next_run_time(t.id)
        
        # 从映射中获取最新执行记录
        latest_exec_info = exec_map.get(t.id)
        if latest_exec_info:
            t.last_execution_status = latest_exec_info['status']
            t.latest_execution_id = latest_exec_info['id']
            t.latest_execution_time = latest_exec_info['start_time']
    
    # 缓存结果（TTL 5秒，因为任务状态可能频繁变化）
    query_cache.set(cache_key, tasks, ttl=5)
    
    return tasks

def resolve_output_dir(project: project_models.Project):
    # Check if project has a specific output directory configured
    if project.output_dir:
        # Check if it's an absolute path
        if os.path.isabs(project.output_dir):
            return project.output_dir
        # If relative, it's relative to project path? Or root?
        # Usually users might enter "/Data" which is absolute in container.
        # But if they enter "data", where is it?
        return project.output_dir

    # Fallback to default /data directory which is mapped to host ./Data
    # In Docker, we map ./Data -> /data.
    # So we should default to /data if no specific output dir is set.
    # However, existing code was trying to resolve relative to backend dir which is wrong for Docker volume mapping.
    
    # Check if we are in Docker (simple check: /data exists and is a directory)
    if os.path.exists("/data") and os.path.isdir("/data"):
        return "/data"
        
    # Local development fallback (Windows/Mac host without Docker)
    # We assume the project root is 2 levels up from this file (backend/task_service/task_router.py -> backend)
    # And Data is sibling to backend.
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(backend_dir)
    data_dir = os.path.join(root_dir, "Data")
    if os.path.exists(data_dir):
        return data_dir
        
    return None

def resolve_test_output_dir():
    """Resolve the test output directory: /data/test"""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(backend_dir)
    test_dir = os.path.join(root_dir, "Data", "test")
    return test_dir

def parse_task_ids(task_ids: str):
    if not task_ids:
        return []
    parts = [p.strip() for p in task_ids.split(",")]
    return [int(p) for p in parts if p.isdigit()]

@router.get("/test-metrics/overview", response_model=schemas.TestMetricsOverview)
async def get_test_metrics_overview(project_id: int = None, task_ids: str = None, window_seconds: int = 10, sample_limit: int = 50, db: Session = Depends(get_db)):
    """
    获取测试指标概览
    
    - **project_id**: 可选，项目 ID
    - **task_ids**: 可选，逗号分隔的任务 ID 列表（如 "1,2,3"）
    - **window_seconds**: 时间窗口（秒），用于统计最近的文件产出和执行情况（默认10秒）
    - **sample_limit**: 返回的文件样本数量限制（默认50）
    
    返回包括：
    - 产出文件统计（总数、大小、类型分布）
    - 执行窗口统计（开始、完成、成功、失败、运行中）
    - 最新执行记录
    - 时间序列数据（持续时间、CPU、内存）
    - 输出延迟统计
    - 文件样本和日志文件列表
    """
    ids = parse_task_ids(task_ids)
    project = None
    tasks = []

    if ids:
        tasks = db.query(models.Task).filter(models.Task.id.in_(ids)).all()
        if not tasks:
            raise HTTPException(status_code=404, detail="No tasks found for provided IDs")
        # Infer project from the first task
        # We assume all tasks belong to the same project for metrics aggregation context
        # If mixed, we just pick the first one's project for output directory resolution
        first_task_pid = tasks[0].project_id
        project = db.query(project_models.Project).filter(project_models.Project.id == first_task_pid).first()
    elif project_id:
        project = db.query(project_models.Project).filter(project_models.Project.id == project_id).first()
        tasks = db.query(models.Task).filter(models.Task.project_id == project_id).all()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or could not be inferred from tasks")
    project_id = project.id

    # Use test output directory: /data/test
    output_dir = resolve_test_output_dir()

    # Ensure test output directory exists
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

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
        # Optimization: If directory is large, os.walk can be slow.
        # But for now we assume it's manageable.
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
                
                # Check if file was modified within the window
                # Also consider creation time (st_ctime) on Windows, but st_mtime is usually enough for "throughput"
                # If file is being written to, mtime updates.
                # However, st_mtime might be in local time or UTC depending on OS.
                # datetime.datetime.now().timestamp() is local time.
                # os.stat().st_mtime is epoch time. They should match.
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
    running = exec_query.filter(models.TaskExecution.status.in_(["running", "pending"])).count()

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
    parse_series = []
    index_series = []
    api_series = []
    
    for e in reversed(series_execs):
        label = e.start_time.strftime("%m-%d %H:%M:%S") if e.start_time else str(e.id)
        duration_series.append({"label": label, "value": float(e.duration or 0)})
        cpu_series.append({"label": label, "value": float(e.max_cpu_percent or 0)})
        mem_series.append({"label": label, "value": float(e.max_memory_mb or 0)})

    recent_sample_pairs = []
    try:
        start_times = [item.get("start_time") for item in latest_executions if item.get("start_time") and item.get("start_time") >= start_window]
        recent_samples = [s for s in samples if s["mtime"] >= start_window]
        start_times_sorted = sorted([st for st in start_times if st], key=lambda x: x)
        for s in recent_samples:
            st_candidate = None
            for st in reversed(start_times_sorted):
                if st <= s["mtime"]:
                    st_candidate = st
                    break
            if st_candidate:
                latency = (s["mtime"] - st_candidate).total_seconds()
                recent_sample_pairs.append((s["mtime"], latency))
    except Exception:
        recent_sample_pairs = []

    first_latency = min([lat for _, lat in recent_sample_pairs]) if recent_sample_pairs else None
    last_latency = recent_sample_pairs[-1][1] if recent_sample_pairs else None
    avg_latency = (sum([lat for _, lat in recent_sample_pairs]) / len(recent_sample_pairs)) if recent_sample_pairs else None
    latency_stats = {
        "first_output_latency_seconds": first_latency,
        "avg_output_latency_seconds": avg_latency,
        "last_output_latency_seconds": last_latency,
        "sample_count": len(recent_sample_pairs)
    }

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
            "max_memory": mem_series,
            "parse_time": parse_series,
            "index_time": index_series,
            "api_time": api_series
        },
        "latency": latency_stats,
        "evidence": {
            "output_samples": output_samples,
            "log_files": log_files
        }
    }

@router.post("/test-metrics/clear-output")
async def clear_test_output():
    """
    清理测试输出目录
    
    删除 /data/test 目录下的所有文件和空目录。
    返回删除的文件数量和总大小。
    """
    import shutil

    test_dir = resolve_test_output_dir()

    if not test_dir:
        raise HTTPException(status_code=500, detail="Cannot resolve test output directory")

    deleted_count = 0
    deleted_size = 0

    try:
        if os.path.exists(test_dir):
            for root, dirs, files in os.walk(test_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        deleted_size += os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception:
                        pass
                # Remove empty directories
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        os.rmdir(dir_path)
                    except Exception:
                        pass

        return {
            "success": True,
            "message": f"已清理 {deleted_count} 个文件，共 {format_bytes(deleted_size)}",
            "deleted_count": deleted_count,
            "deleted_size": deleted_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

def format_bytes(size):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

@router.get("/test-metrics/export")
async def export_test_metrics(project_id: int = None, task_ids: str = None, window_seconds: int = 10, sample_limit: int = 10000, format: str = "json", db: Session = Depends(get_db)):
    """
    导出测试指标数据
    
    - **project_id**: 可选，项目 ID
    - **task_ids**: 可选，逗号分隔的任务 ID 列表
    - **window_seconds**: 时间窗口（秒）
    - **sample_limit**: 文件样本数量限制（默认10000）
    - **format**: 导出格式，支持 "json" 或 "csv"（默认json）
    
    返回文件流，包含完整的测试报告：
    - 元数据（项目信息、导出时间）
    - 汇总统计（文件数、吞吐量）
    - 性能指标（CPU峰值、内存峰值、平均耗时）
    - 执行详情
    - 时间序列数据
    - 吞吐量趋势
    - 产出样本
    """
    metrics = await get_test_metrics_overview(project_id, task_ids, window_seconds, sample_limit, db)
    payload = jsonable_encoder(metrics)
    fmt = (format or "json").lower()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_metrics_project_{project_id}_{timestamp}.{fmt}"

    # Calculate throughput series from output samples
    # Bucket by 1-second intervals
    throughput_series = {}
    for sample in payload.get("evidence", {}).get("output_samples", []):
        mtime_str = sample.get("mtime")
        if mtime_str:
            # Parse datetime string back to timestamp bucket (or just use string if ISO)
            # ISO format: YYYY-MM-DDTHH:MM:SS.ssssss
            try:
                dt = datetime.datetime.fromisoformat(mtime_str)
                key = dt.strftime("%Y-%m-%d %H:%M:%S")
                if key not in throughput_series:
                    throughput_series[key] = {"files": 0, "bytes": 0}
                throughput_series[key]["files"] += 1
                throughput_series[key]["bytes"] += sample.get("size", 0)
            except Exception:
                pass
    
    sorted_throughput = [{"time": k, "files": v["files"], "bytes": v["bytes"]} for k, v in sorted(throughput_series.items())]

    if fmt == "json":
        # Create a more structured report for JSON
        report = {
            "meta": {
                "project_id": payload.get("project_id"),
                "project_name": payload.get("project_name"),
                "export_time": timestamp,
                "window_seconds": payload.get("window_seconds")
            },
            "summary": {
                "total_files": payload.get("output", {}).get("total_files"),
                "total_bytes": payload.get("output", {}).get("total_bytes"),
                "throughput_files_per_sec": payload.get("output", {}).get("recent_files", 0) / (window_seconds or 1),
                "throughput_mb_per_sec": (payload.get("output", {}).get("recent_bytes", 0) / 1024 / 1024) / (window_seconds or 1),
            },
            "performance": {
                "cpu_peak_percent": max([e.get("max_cpu_percent") or 0 for e in payload.get("latest_executions", [])] or [0]),
                "memory_peak_mb": max([e.get("max_memory_mb") or 0 for e in payload.get("latest_executions", [])] or [0]),
                "avg_duration_sec": sum([e.get("duration") or 0 for e in payload.get("latest_executions", [])]) / len(payload.get("latest_executions", [])) if payload.get("latest_executions") else 0
            },
            "executions": payload.get("latest_executions", []),
            "time_series": payload.get("timeseries", {}),
            "throughput_series": sorted_throughput,
            "output_samples": payload.get("evidence", {}).get("output_samples", [])
        }
        
        content = json.dumps(report, ensure_ascii=False, indent=2)
        return StreamingResponse(io.BytesIO(content.encode("utf-8")), media_type="application/json", headers={
            "Content-Disposition": f"attachment; filename={filename}"
        })
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        # 1. Summary Section
        writer.writerow(["=== 测试报告汇总 ==="])
        writer.writerow(["项目 ID", payload.get("project_id")])
        writer.writerow(["项目名称", payload.get("project_name")])
        writer.writerow(["导出时间", timestamp])
        writer.writerow([])
        
        # 2. Performance Metrics
        writer.writerow(["=== 核心性能指标 ==="])
        writer.writerow(["指标", "数值", "单位"])
        writer.writerow(["产出文件总数", payload.get("output", {}).get("total_files"), "个"])
        writer.writerow(["产出数据总量", payload.get("output", {}).get("total_bytes"), "bytes"])
        writer.writerow(["吞吐量 (文件/秒)", f"{payload.get('output', {}).get('recent_files', 0) / (window_seconds or 1):.2f}", "files/s"])
        writer.writerow(["吞吐量 (MB/秒)", f"{(payload.get('output', {}).get('recent_bytes', 0) / 1024 / 1024) / (window_seconds or 1):.2f}", "MB/s"])
        
        cpu_peak = max([e.get("max_cpu_percent") or 0 for e in payload.get("latest_executions", [])] or [0])
        mem_peak = max([e.get("max_memory_mb") or 0 for e in payload.get("latest_executions", [])] or [0])
        writer.writerow(["CPU 峰值", f"{cpu_peak:.2f}", "%"])
        writer.writerow(["内存峰值", f"{mem_peak:.2f}", "MB"])
        writer.writerow([])
        
        # 3. Throughput Series (New)
        writer.writerow(["=== 吞吐量趋势 (时间序列) ==="])
        writer.writerow(["时间点", "文件数", "数据量(Bytes)"])
        for item in sorted_throughput:
            writer.writerow([item["time"], item["files"], item["bytes"]])
        writer.writerow([])

        # 4. Execution Details
        writer.writerow(["=== 任务执行详情 ==="])
        writer.writerow(["任务 ID", "任务名称", "状态", "开始时间", "耗时(秒)", "CPU使用率(%)", "内存使用(MB)"])
        for item in payload.get("latest_executions", []):
            writer.writerow([
                item.get("task_id"),
                item.get("task_name"),
                item.get("status"),
                item.get("start_time"),
                item.get("duration"),
                item.get("max_cpu_percent"),
                item.get("max_memory_mb")
            ])
        writer.writerow([])
        
        # 5. Output Samples
        writer.writerow(["=== 产出样本 (Top 50) ==="])
        writer.writerow(["文件名", "大小(Bytes)", "修改时间"])
        for item in payload.get("evidence", {}).get("output_samples", []):
            writer.writerow([item.get("name"), item.get("size"), item.get("mtime")])
            
        content = buffer.getvalue()
        return StreamingResponse(io.BytesIO(content.encode("utf-8")), media_type="text/csv", headers={
            "Content-Disposition": f"attachment; filename={filename}"
        })
    raise HTTPException(status_code=400, detail="Invalid format, use json or csv")

@router.get("/{task_id}", response_model=schemas.Task)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    获取单个任务的详细信息
    
    - **task_id**: 任务 ID
    
    返回任务对象，包含 next_run 字段（下次运行时间）
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.next_run = task_manager.get_next_run_time(task.id)
    return task

@router.put("/{task_id}", response_model=schemas.Task)
async def update_task(task_id: int, task_update: schemas.TaskUpdate, request: Request, db: Session = Depends(get_db)):
    """
    更新任务配置
    
    - **task_id**: 任务 ID
    - **task_update**: 要更新的字段（部分更新，只传需要修改的字段）
    
    如果更新了关键字段（trigger_type, trigger_value, command, env_id, project_id, status, timeout, retry_count, retry_delay），
    会自动重新调度任务。
    """
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
    """
    暂停任务
    
    - **task_id**: 任务 ID
    
    将任务状态设置为 paused，并从调度器中暂停该任务。
    正在运行的任务不会被停止，但不会触发新的执行。
    """
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
    """
    恢复任务
    
    - **task_id**: 任务 ID
    
    将任务状态设置为 active，并重新添加到调度器中。
    如果任务在调度器中不存在，会重新创建调度任务。
    """
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
    """
    删除任务
    
    - **task_id**: 任务 ID
    
    从调度器中移除任务，并从数据库中删除。
    注意：此操作不可恢复，但不会删除任务的执行历史记录。
    """
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
    """
    手动触发任务执行
    
    - **task_id**: 任务 ID
    
    立即创建一个执行记录并在后台运行任务。
    返回执行 ID，可用于跟踪执行状态和查看日志。
    """
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
    """
    停止正在运行的任务执行
    
    - **execution_id**: 执行 ID
    
    终止正在运行的进程，并将执行状态更新为 stopped。
    如果执行已完成或不存在，返回相应提示。
    """
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
    """
    删除任务执行记录
    
    - **execution_id**: 执行 ID
    
    如果执行正在运行，会先尝试停止。
    删除执行记录和关联的日志文件。
    """
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
        except Exception:
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
    """
    获取任务的所有执行记录
    
    - **task_id**: 任务 ID
    
    返回该任务的执行历史记录，按开始时间倒序排列，最多返回100条。
    """
    return db.query(models.TaskExecution).filter(models.TaskExecution.task_id == task_id).order_by(models.TaskExecution.start_time.desc()).limit(100).all()

@router.get("/executions/{execution_id}/log")
async def get_execution_log(execution_id: int, tail_kb: int = Query(None), db: Session = Depends(get_db)):
    """
    获取任务执行的日志内容
    
    - **execution_id**: 执行 ID
    - **tail_kb**: 可选，只返回最后 N KB 的日志（用于大日志文件）
    
    如果日志文件不存在，返回数据库中存储的 output 字段内容。
    """
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
    """
    在任务执行日志中搜索关键词
    
    - **execution_id**: 执行 ID
    - **q**: 搜索关键词（至少1个字符）
    - **limit**: 返回的最大结果数（默认100）
    
    返回匹配的行号和内容，不区分大小写。
    """
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
    """
    WebSocket 实时日志流
    
    - **execution_id**: 执行 ID
    
    建立 WebSocket 连接后，实时推送日志内容。
    初始发送最后50KB的日志，然后持续推送新产生的日志行。
    适用于实时查看正在运行的任务日志。
    """
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
        logger.info(f"Client disconnected from log {execution_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
        except Exception:
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
    """
    预览 Cron 表达式的下次执行时间
    
    - **cron_expression**: Cron 表达式（如 "0 0 * * *"）
    
    返回接下来5次的执行时间，用于验证 Cron 表达式是否正确。
    """
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
