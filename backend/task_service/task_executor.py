"""
任务执行模块 - 负责任务的实际执行逻辑（环境准备、命令执行、重试）
"""
import os
import shlex
import subprocess
import datetime
from core.database import SessionLocal
from core.config import settings
from core.logging import get_logger
from core.security import decrypt_value
from core.concurrency import concurrency_controller
from task_service import models
from task_service.process_manager import process_manager
from project_service import models as project_models
from environment_service import models as env_models
from system_service import models as system_models

logger = get_logger(__name__)


def run_task_execution(task_id: int, attempt: int = 1, execution_id: int = None, scheduler=None):
    """
    执行任务
    
    Args:
        task_id: 任务 ID
        attempt: 重试次数（从1开始）
        execution_id: 可选的执行 ID（如果已创建执行记录）
        scheduler: APScheduler 实例（用于重试调度）
    """
    # 获取并发控制许可（超时30秒）
    acquired = concurrency_controller.acquire(timeout=30.0)
    if not acquired:
        logger.warning(f"Task {task_id} execution skipped: no available concurrency slot")
        return
    
    db = None
    try:
        db = SessionLocal()
        execution = None
        if execution_id:
            execution = db.query(models.TaskExecution).filter(
                models.TaskExecution.id == execution_id
            ).first()
            if execution:
                # Update existing execution to running
                execution.status = "running"
                # Update start time to actual execution start
                execution.start_time = datetime.datetime.now()
                db.commit()
                # Ensure we use the task_id from the execution record if available, or the passed one
                if execution.task_id:
                    task_id = execution.task_id

        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            logger.warning(f"Task {task_id} not found, execution skipped.")
            return

        # Create Execution Record if not provided (Scheduler mode)
        if not execution:
            execution = models.TaskExecution(
                task_id=task.id,
                status="running",
                attempt=attempt,
                start_time=datetime.datetime.now()
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)
        
        # Prepare Environment and Path
        project = db.query(project_models.Project).filter(
            project_models.Project.id == task.project_id
        ).first()
        if not project:
            raise Exception("Project not found")

        # Working Directory
        cwd = project.path
        if task.project_id:
            # If work_dir is relative, join with project path
            if project.work_dir and project.work_dir != "./":
                cwd = os.path.join(project.path, project.work_dir)

        # Command
        cmd = task.command
        
        # Environment (Python Interpreter)
        env_vars = os.environ.copy()
        # Force unbuffered output for real-time logging
        env_vars["PYTHONUNBUFFERED"] = "1"
        
        # Inject Global Environment Variables (Kumo)
        try:
            kumo_env_vars = db.query(system_models.EnvironmentVariable).all()
            for ev in kumo_env_vars:
                # Decrypt if secret
                if ev.is_secret:
                    val = decrypt_value(ev.value)
                else:
                    val = ev.value
                
                env_vars[ev.key] = val
            
            # Inject Network Proxy (If Enabled)
            proxy_enabled = db.query(system_models.SystemConfig).filter(
                system_models.SystemConfig.key == "proxy.enabled"
            ).first()
            if proxy_enabled and proxy_enabled.value == "true":
                proxy_url = db.query(system_models.SystemConfig).filter(
                    system_models.SystemConfig.key == "proxy.url"
                ).first()
                if proxy_url and proxy_url.value:
                    p_url = proxy_url.value
                    env_vars["http_proxy"] = p_url
                    env_vars["https_proxy"] = p_url
                    env_vars["all_proxy"] = p_url
                    env_vars["HTTP_PROXY"] = p_url
                    env_vars["HTTPS_PROXY"] = p_url
                    env_vars["ALL_PROXY"] = p_url
                    logger.debug(f"Injected global proxy: {p_url}")

        except Exception as e:
            logger.error(f"Error injecting Kumo environment variables: {e}")
        
        # Inject Output Path Override if project has one
        if project.output_dir:
            # We inject this as specific env vars that generic spiders might check
            # Or users can use os.environ.get('OUTPUT_DIR') in their scripts
            env_vars["OUTPUT_DIR"] = project.output_dir
            env_vars["DATA_DIR"] = project.output_dir
            env_vars["BASE_DATA_DIR"] = project.output_dir

            # Ensure the directory exists (in container context)
            if not os.path.exists(project.output_dir):
                try:
                    os.makedirs(project.output_dir, exist_ok=True)
                except Exception as e:
                    logger.warning(f"Could not create output dir {project.output_dir}: {e}")

        # Inject Rate Limiting Config (for爬虫高频请求控制)
        if task.request_interval and task.request_interval > 0:
            env_vars["REQUEST_INTERVAL_MS"] = str(task.request_interval)
            logger.debug(f"Injected REQUEST_INTERVAL_MS: {task.request_interval}ms")

        if task.max_requests_per_second and task.max_requests_per_second > 0:
            env_vars["MAX_REQUESTS_PER_SECOND"] = str(task.max_requests_per_second)
            logger.debug(f"Injected MAX_REQUESTS_PER_SECOND: {task.max_requests_per_second}/s")

        # Inject Resource Limits Config
        if task.max_cpu_percent and task.max_cpu_percent > 0:
            env_vars["MAX_CPU_PERCENT"] = str(task.max_cpu_percent)
            logger.debug(f"Injected MAX_CPU_PERCENT: {task.max_cpu_percent}%")

        if task.max_memory_mb and task.max_memory_mb > 0:
            env_vars["MAX_MEMORY_MB"] = str(task.max_memory_mb)
            logger.debug(f"Injected MAX_MEMORY_MB: {task.max_memory_mb}MB")

        python_path = "python"  # Default
        
        if task.env_id:
            env = db.query(env_models.PythonVersion).filter(
                env_models.PythonVersion.id == task.env_id
            ).first()
            if env:
                python_path = env.path
                
                # Docker Compatibility Fix:
                # Check if file exists. If not, fallback to "python" (system python)
                if not os.path.exists(python_path):
                    logger.warning(
                        f"Interpreter {python_path} not found. Falling back to system 'python'."
                    )
                    python_path = "python"
                
                # Add env to PATH if needed, or just use full path to python
                # If it's a conda env, we might need activation, but usually running python executable directly works for scripts
                # We can prepend env bin to PATH
                env_bin = os.path.dirname(env.path)
                env_vars["PATH"] = f"{env_bin}{os.pathsep}{env_vars.get('PATH', '')}"

        # If command starts with "python", replace it with specific python path
        if cmd.strip().startswith("python "):
            cmd = f"\"{python_path}\" {cmd.strip()[7:]}"
        elif cmd.strip() == "python":
            cmd = python_path
            
        logger.info(f"Executing Task {task.name} (ID: {task.id}): {cmd} in {cwd}")

        # Prepare Log File
        log_dir = settings.task_log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        log_file_path = os.path.join(log_dir, f"task_{task.id}_exec_{execution.id}.log")
        execution.log_file = log_file_path
        db.commit()

        # Execute
        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                # Parse command string to list for shell=False safety
                args = shlex.split(cmd)

                # Create new process group for proper subprocess cleanup
                # This ensures all child processes (like chromedriver) are terminated together
                process = subprocess.Popen(
                    args,
                    shell=False,
                    cwd=cwd,
                    env=env_vars,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    start_new_session=True  # Create process group for proper cleanup
                )

                # Register process with process manager
                process_manager.register_process(execution.id, process)
                
                try:
                    # Wait with timeout
                    timeout_val = task.timeout if task.timeout else 3600
                    process.wait(timeout=timeout_val)
                    
                    if process.returncode == 0:
                        execution.status = "success"
                    else:
                        execution.status = "failed"
                        
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"Task {task.id} execution {execution.id} timed out after {timeout_val}s."
                    )
                    process.kill()
                    execution.status = "timeout"
                    
                # Remove from running processes
                process_manager.unregister_process(execution.id)
                
            execution.end_time = datetime.datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            # Save Resource Stats
            stats = process_manager.get_stats(execution.id)
            if stats:
                execution.max_cpu_percent = stats.get('max_cpu')
                execution.max_memory_mb = stats.get('max_mem')
                # Cleanup stats
                process_manager.cleanup_stats(execution.id)
            
            # Read back some output for the DB record (optional, maybe first 4KB)
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    execution.output = f.read(4096)
            except Exception:
                execution.output = "See log file."
            
            if execution.status == "timeout":
                execution.output = (execution.output or "") + f"\n[Timeout after {timeout_val}s]"

            db.commit()

            # Retry Logic
            if execution.status in ["failed", "timeout"]:
                # Update consecutive failures count
                task.consecutive_failures = (task.consecutive_failures or 0) + 1
                db.commit()

                # Circuit breaker: auto-pause task if too many consecutive failures
                failure_threshold = task.failure_threshold or 5
                if task.consecutive_failures >= failure_threshold:
                    task.status = "paused"
                    db.commit()
                    logger.warning(
                        f"[CIRCUIT BREAKER] Task {task.id} paused due to "
                        f"{task.consecutive_failures} consecutive failures "
                        f"(threshold: {failure_threshold})"
                    )

                retry_count = task.retry_count or 0
                if attempt <= retry_count and scheduler:
                    delay = task.retry_delay or 60
                    next_run = datetime.datetime.now() + datetime.timedelta(seconds=delay)
                    logger.info(
                        f"Task {task.id} failed. Scheduling retry {attempt + 1}/{retry_count + 1} "
                        f"in {delay}s."
                    )

                    # Schedule retry
                    scheduler.add_job(
                        run_task_execution,
                        trigger='date',
                        run_date=next_run,
                        args=[task.id, attempt + 1, None, scheduler],
                        id=f"retry_{task.id}_{execution.id}"
                    )
            else:
                # Reset consecutive failures on success
                if task.consecutive_failures and task.consecutive_failures > 0:
                    task.consecutive_failures = 0
                    db.commit()
                    logger.info(f"Task {task.id} succeeded. Reset consecutive failures count.")

        except Exception as e:
            raise e
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        if db and 'execution' in locals() and execution:
            try:
                execution.status = "failed"
                execution.end_time = datetime.datetime.now()
                execution.output = str(e)
                db.commit()
            except Exception:
                pass
    finally:
        # 释放并发控制许可
        concurrency_controller.release()
        if db:
            db.close()
