import os
import sys
import subprocess
import shlex
import datetime
import logging
import json
import requests # Added
import psutil # Added
import threading
import time
import signal
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from core.database import SessionLocal
from task_service import models
from project_service import models as project_models
from environment_service import models as env_models
from system_service import models as system_models
from core.security import decrypt_value

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('apscheduler')
logger.setLevel(logging.INFO)  # 改为 INFO 级别，减少日志输出

class TaskManager:
    _instance = None
    scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            
            # High Performance Concurrency Config
            max_workers = int(os.environ.get('MAX_CONCURRENT_TASKS', 20))
            executors = {
                'default': ThreadPoolExecutor(max_workers),
                'processpool': ProcessPoolExecutor(5)
            }
            job_defaults = {
                'coalesce': False,
                'max_instances': 3
            }
            
            print(f"[TaskManager] Initializing with max_workers={max_workers}")
            cls._instance.scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults)
            # cls._instance.scheduler.start() # Do not auto start
        return cls._instance

    def start(self):
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            print("Scheduler started.")
            
            # Start monitor thread
            monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
            monitor_thread.start()
            print("Resource monitor started.")

    def shutdown(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            print("Scheduler shutdown.")

    def add_job(self, task_id: int, trigger_type: str, trigger_value: str, status: str, priority: int = 0):
        # Remove existing job if any
        self.remove_job(task_id)
        
        if status != 'active':
            return

        trigger = None
        try:
            # Map priority to executor or other APScheduler features if needed
            # Currently APScheduler doesn't support strict priority queues out of the box for SimpleTrigger
            # But we can use 'coalesce' or separate executors if needed. 
            # For now, we just pass it, but maybe we can use it to decide WHICH executor to use?
            # E.g. priority > 0 -> use a dedicated thread pool?
            # Let's keep it simple: just schedule it.
            
            if trigger_type == 'interval':
                # trigger_value example: {"value": 1, "unit": "hours"}
                if isinstance(trigger_value, str):
                    val = json.loads(trigger_value)
                else:
                    val = trigger_value
                
                kwargs = {val['unit']: int(val['value'])}
                trigger = IntervalTrigger(**kwargs)
                
            elif trigger_type == 'cron':
                # trigger_value example: "* * * * *"
                trigger = CronTrigger.from_crontab(trigger_value)
                
            elif trigger_type == 'date':
                # trigger_value example: "2025-12-07T12:00:00"
                trigger = DateTrigger(run_date=trigger_value)
            
            elif trigger_type == 'immediate':
                return 

            if trigger:
                self.scheduler.add_job(
                    run_task_execution,
                    trigger=trigger,
                    args=[task_id],
                    id=str(task_id),
                    replace_existing=True,
                    priority=priority # APScheduler doesn't natively use this for ordering in ThreadPool, but we can store it.
                    # Actually APScheduler jobs don't have 'priority' arg in add_job unless we use a custom job store.
                    # Standard workaround: The order is determined by next_run_time.
                    # If multiple jobs run at SAME time, creation order matters.
                    # We can't easily force priority without a custom scheduler.
                    # However, we CAN pass it to the function execution context if needed.
                )
                print(f"Job {task_id} added with trigger {trigger}")

        except Exception as e:
            print(f"Failed to add job {task_id}: {e}")

    def remove_job(self, task_id: int):
        job_id = str(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    def pause_job(self, task_id: int):
        job_id = str(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)

    def resume_job(self, task_id: int):
        job_id = str(task_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            
    def get_next_run_time(self, task_id: int):
        job = self.scheduler.get_job(str(task_id))
        if job:
            return job.next_run_time
        return None

    def stop_execution(self, execution_id: int):
        """
        Terminates a running execution process and all its child processes.
        Uses process group to ensure all children are killed.
        """
        if execution_id in self.running_processes:
            process = self.running_processes[execution_id]
            try:
                # Kill the entire process group to ensure child processes are terminated
                pgid = self.process_groups.get(execution_id)
                if pgid:
                    try:
                        # Kill the whole process group
                        os.killpg(pgid, signal.SIGTERM)
                        print(f"Terminated process group {pgid} for execution {execution_id}")
                    except ProcessLookupError:
                        # Process group may already be gone
                        pass
                else:
                    # Fallback to single process kill
                    process.terminate()
                    print(f"Terminated execution {execution_id}")

                return True
            except Exception as e:
                print(f"Failed to terminate execution {execution_id}: {e}")
                return False
        return False

    running_processes = {} # execution_id -> subprocess.Popen
    process_groups = {}  # execution_id -> process group ID (pgid)
    execution_stats = {} # execution_id -> {'max_cpu': 0.0, 'max_mem': 0.0}
    psutil_processes = {} # execution_id -> psutil.Process (cached)

    # Maximum cache size to prevent memory leaks
    MAX_CACHE_SIZE = 1000
    _cleanup_counter = 0  # Counter for periodic cleanup

    def _cleanup_caches(self):
        """Clean up stale entries from caches to prevent memory leaks."""
        # Clean up execution_stats for executions that are no longer running
        try:
            from core.database import SessionLocal
            db = SessionLocal()
            try:
                # Get all running execution IDs
                running_ids = set(self.running_processes.keys())

                # Remove stats for finished executions
                stale_stats = []
                for exec_id in list(self.execution_stats.keys()):
                    if exec_id not in running_ids:
                        stale_stats.append(exec_id)

                for exec_id in stale_stats:
                    del self.execution_stats[exec_id]

                # Also clean up psutil_processes cache
                stale_psutil = []
                for exec_id in list(self.psutil_processes.keys()):
                    if exec_id not in running_ids:
                        stale_psutil.append(exec_id)

                for exec_id in stale_psutil:
                    del self.psutil_processes[exec_id]

                # Hard limit: if caches are too large, remove oldest entries
                if len(self.execution_stats) > self.MAX_CACHE_SIZE:
                    # Remove oldest entries (first 50%)
                    keys_to_remove = list(self.execution_stats.keys())[:len(self.execution_stats) // 2]
                    for k in keys_to_remove:
                        del self.execution_stats[k]
                        if k in self.psutil_processes:
                            del self.psutil_processes[k]

            finally:
                db.close()
        except Exception as e:
            print(f"Cache cleanup error: {e}")

    def _monitor_resources(self):
        """
        Background thread to monitor resource usage of running tasks.
        """
        while True:
            try:
                # Periodic cache cleanup every 60 iterations (approx. 60 seconds)
                self._cleanup_counter += 1
                if self._cleanup_counter >= 60:
                    self._cleanup_caches()
                    self._cleanup_counter = 0

                # Iterate over a copy of keys to avoid runtime change issues
                exec_ids = list(self.running_processes.keys())
                
                # Cleanup cache for finished processes
                cached_ids = list(self.psutil_processes.keys())
                for cid in cached_ids:
                    if cid not in self.running_processes:
                        del self.psutil_processes[cid]

                for exec_id in exec_ids:
                    process = self.running_processes.get(exec_id)
                    if process and process.poll() is None:
                        try:
                            # Get or Create cached psutil Process
                            if exec_id in self.psutil_processes:
                                p = self.psutil_processes[exec_id]
                            else:
                                pid = process.pid
                                p = psutil.Process(pid)
                                self.psutil_processes[exec_id] = p
                                # First call always returns 0.0, so we just prime it
                                p.cpu_percent(interval=None)
                            
                            # Get stats (cpu_percent needs interval=None to be non-blocking)
                            # Subsequent calls on the SAME object return valid delta
                            cpu = p.cpu_percent(interval=None)
                            mem_info = p.memory_info()
                            mem_mb = mem_info.rss / (1024 * 1024)
                            
                            # Initialize stats if not present
                            if exec_id not in self.execution_stats:
                                self.execution_stats[exec_id] = {'max_cpu': 0.0, 'max_mem': 0.0}
                                
                            stats = self.execution_stats[exec_id]
                            if cpu > stats['max_cpu']:
                                stats['max_cpu'] = cpu
                            if mem_mb > stats['max_mem']:
                                stats['max_mem'] = mem_mb
                            
                            # Update DB periodically (e.g. every 3 seconds) to allow real-time monitoring
                            # We check if it's time to update
                            now = time.time()
                            last_update = stats.get('last_update', 0)
                            if now - last_update > 3:
                                db = SessionLocal()
                                try:
                                    execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == exec_id).first()
                                    if execution:
                                        execution.max_cpu_percent = stats['max_cpu']
                                        execution.max_memory_mb = stats['max_mem']
                                        db.commit()
                                        stats['last_update'] = now
                                except Exception as e:
                                    print(f"Error updating execution stats: {e}")
                                finally:
                                    db.close()
                                
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Process might have died just now
                            if exec_id in self.psutil_processes:
                                del self.psutil_processes[exec_id]
                        except Exception as e:
                            print(f"Error monitoring execution {exec_id}: {e}")
                            
            except Exception as e:
                print(f"Error in resource monitor loop: {e}")
                
            time.sleep(2)  # Check every 2 seconds - reduced from 1s for better performance

    def load_jobs_from_db(self):
        db = SessionLocal()
        try:
            tasks = db.query(models.Task).filter(models.Task.status == 'active').all()
            print(f"Loading {len(tasks)} active tasks from DB...")
            for task in tasks:
                self.add_job(task.id, task.trigger_type, task.trigger_value, task.status, task.priority or 0)
        except Exception as e:
            print(f"Error loading tasks: {e}")
        finally:
            db.close()

task_manager = TaskManager()

def run_task_execution(task_id: int, attempt: int = 1, execution_id: int = None):
    db = SessionLocal()
    try:
        execution = None
        if execution_id:
            execution = db.query(models.TaskExecution).filter(models.TaskExecution.id == execution_id).first()
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
            print(f"Task {task_id} not found execution skipped.")
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
        project = db.query(project_models.Project).filter(project_models.Project.id == task.project_id).first()
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
            proxy_enabled = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == "proxy.enabled").first()
            if proxy_enabled and proxy_enabled.value == "true":
                proxy_url = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == "proxy.url").first()
                if proxy_url and proxy_url.value:
                    p_url = proxy_url.value
                    env_vars["http_proxy"] = p_url
                    env_vars["https_proxy"] = p_url
                    env_vars["all_proxy"] = p_url
                    env_vars["HTTP_PROXY"] = p_url
                    env_vars["HTTPS_PROXY"] = p_url
                    env_vars["ALL_PROXY"] = p_url
                    print(f" injected global proxy: {p_url}")

        except Exception as e:
            print(f"Error injecting Kumo environment variables: {e}")
        
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
                    print(f"Warning: Could not create output dir {project.output_dir}: {e}")

        # Inject Rate Limiting Config (for爬虫高频请求控制)
        if task.request_interval and task.request_interval > 0:
            env_vars["REQUEST_INTERVAL_MS"] = str(task.request_interval)
            print(f" injected REQUEST_INTERVAL_MS: {task.request_interval}ms")

        if task.max_requests_per_second and task.max_requests_per_second > 0:
            env_vars["MAX_REQUESTS_PER_SECOND"] = str(task.max_requests_per_second)
            print(f" injected MAX_REQUESTS_PER_SECOND: {task.max_requests_per_second}/s")

        # Inject Resource Limits Config
        if task.max_cpu_percent and task.max_cpu_percent > 0:
            env_vars["MAX_CPU_PERCENT"] = str(task.max_cpu_percent)
            print(f" injected MAX_CPU_PERCENT: {task.max_cpu_percent}%")

        if task.max_memory_mb and task.max_memory_mb > 0:
            env_vars["MAX_MEMORY_MB"] = str(task.max_memory_mb)
            print(f" injected MAX_MEMORY_MB: {task.max_memory_mb}MB")

        python_path = "python" # Default
        
        if task.env_id:
            env = db.query(env_models.PythonVersion).filter(env_models.PythonVersion.id == task.env_id).first()
            if env:
                python_path = env.path
                
                # Docker Compatibility Fix:
                # If path starts with /opt/conda (typical Docker path) but we are on Windows (local dev),
                # it might be fine if we are NOT running in Docker locally.
                # BUT, if the path was registered as a Windows path (e.g. D:\env\...) and we are running inside Docker, it will fail.
                # Conversely, if registered as /opt/conda... and running on Windows, it fails.
                
                # Current Scenario: User sees "/bin/sh: 1: /opt/conda/envs/dockertest/bin/python: not found"
                # This suggests the task IS trying to use a path that looks like linux path, but maybe it doesn't exist?
                # OR, the environment was registered with a path that is valid on Host but not in Container?
                
                # Check if file exists. If not, fallback to "python" (system python)
                if not os.path.exists(python_path):
                     print(f"Warning: Interpreter {python_path} not found. Falling back to system 'python'.")
                     # Try to see if it's just a path mapping issue?
                     # No, for now just fallback to system python to make it work
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
            
        print(f"Executing Task {task.name} (ID: {task.id}): {cmd} in {cwd}")

        # Prepare Log File
        log_dir = os.path.abspath(os.path.join(os.getcwd(), "logs", "tasks"))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
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

                # Store process handle and PID
                task_manager.running_processes[execution.id] = process
                # Also store the process group ID for killing all children
                task_manager.process_groups[execution.id] = process.pid
                
                try:
                    # Wait with timeout
                    timeout_val = task.timeout if task.timeout else 3600
                    process.wait(timeout=timeout_val)
                    
                    if process.returncode == 0:
                        execution.status = "success"
                    else:
                        execution.status = "failed"
                        
                except subprocess.TimeoutExpired:
                    print(f"Task {task.id} execution {execution.id} timed out after {timeout_val}s.")
                    process.kill()
                    execution.status = "timeout"
                    # Read partial output if any
                    
                # Remove from running processes
                if execution.id in task_manager.running_processes:
                    del task_manager.running_processes[execution.id]
                # Clean up process group
                if execution.id in task_manager.process_groups:
                    del task_manager.process_groups[execution.id]
                
            execution.end_time = datetime.datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            # Save Resource Stats
            if execution.id in task_manager.execution_stats:
                stats = task_manager.execution_stats[execution.id]
                execution.max_cpu_percent = stats.get('max_cpu')
                execution.max_memory_mb = stats.get('max_mem')
                # Cleanup stats
                del task_manager.execution_stats[execution.id]
            
            # Read back some output for the DB record (optional, maybe first 4KB)
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    execution.output = f.read(4096) 
            except:
                execution.output = "See log file."
            
            if execution.status == "timeout":
                execution.output = (execution.output or "") + f"\n[Timeout after {timeout_val}s]"

            db.commit()

# ...

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
                    print(f"[CIRCUIT BREAKER] Task {task.id} paused due to {task.consecutive_failures} consecutive failures (threshold: {failure_threshold})")

                retry_count = task.retry_count or 0
                if attempt <= retry_count:
                    delay = task.retry_delay or 60
                    next_run = datetime.datetime.now() + datetime.timedelta(seconds=delay)
                    print(f"Task {task.id} failed. Scheduling retry {attempt + 1}/{retry_count + 1} in {delay}s.")

                    # Schedule retry
                    task_manager.scheduler.add_job(
                        run_task_execution,
                        trigger='date',
                        run_date=next_run,
                        args=[task.id, attempt + 1],
                        id=f"retry_{task.id}_{execution.id}"
                    )
            else:
                # Reset consecutive failures on success
                if task.consecutive_failures and task.consecutive_failures > 0:
                    task.consecutive_failures = 0
                    db.commit()
                    print(f"Task {task.id} succeeded. Reset consecutive failures count.")

        except Exception as e:
            raise e
        
    except Exception as e:
        print(f"Task {task_id} failed: {e}")
        if 'execution' in locals():
            execution.status = "failed"
            execution.end_time = datetime.datetime.now()
            execution.output = str(e)
            db.commit()
    finally:
        db.close()
