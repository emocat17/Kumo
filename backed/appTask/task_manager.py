import os
import sys
import subprocess
import datetime
import logging
import json
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from app.database import SessionLocal
from appTask import models
from appProject import models as project_models
from appEnv import models as env_models

# Setup logging
logging.basicConfig()
logger = logging.getLogger('apscheduler')
logger.setLevel(logging.DEBUG)

class TaskManager:
    _instance = None
    scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance.scheduler = BackgroundScheduler()
            cls._instance.scheduler.start()
        return cls._instance

    def add_job(self, task_id: int, trigger_type: str, trigger_value: str, status: str):
        # Remove existing job if any
        self.remove_job(task_id)
        
        if status != 'active':
            return

        trigger = None
        try:
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
                # APScheduler cron: second, minute, hour, day, month, day_of_week, year
                # We assume standard 5-part cron or 6-part?
                # Let's assume standard cron string and parse it to kwargs or use from_crontab if available
                # APScheduler CronTrigger.from_crontab(trigger_value)
                trigger = CronTrigger.from_crontab(trigger_value)
                
            elif trigger_type == 'date':
                # trigger_value example: "2025-12-07T12:00:00"
                trigger = DateTrigger(run_date=trigger_value)
            
            elif trigger_type == 'immediate':
                # Immediate tasks are run once manually, usually not scheduled persistently
                # But if added via UI as "Immediate", maybe run once now?
                # We'll handle immediate separately.
                return 

            if trigger:
                self.scheduler.add_job(
                    run_task_execution,
                    trigger=trigger,
                    args=[task_id],
                    id=str(task_id),
                    replace_existing=True
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
        Terminates a running execution process.
        """
        if execution_id in self.running_processes:
            process = self.running_processes[execution_id]
            try:
                process.terminate() # Or kill()
                print(f"Terminated execution {execution_id}")
                return True
            except Exception as e:
                print(f"Failed to terminate execution {execution_id}: {e}")
                return False
        return False

    running_processes = {} # execution_id -> subprocess.Popen

    def load_jobs_from_db(self):
        db = SessionLocal()
        try:
            tasks = db.query(models.Task).filter(models.Task.status == 'active').all()
            print(f"Loading {len(tasks)} active tasks from DB...")
            for task in tasks:
                self.add_job(task.id, task.trigger_type, task.trigger_value, task.status)
        except Exception as e:
            print(f"Error loading tasks: {e}")
        finally:
            db.close()

task_manager = TaskManager()

def run_task_execution(task_id: int):
    db = SessionLocal()
    try:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            print(f"Task {task_id} not found execution skipped.")
            return

        # Create Execution Record
        execution = models.TaskExecution(
            task_id=task.id,
            status="running",
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
        python_path = "python" # Default
        
        if task.env_id:
            env = db.query(env_models.PythonVersion).filter(env_models.PythonVersion.id == task.env_id).first()
            if env:
                python_path = env.path
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
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    env=env_vars,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # Store process handle
                task_manager.running_processes[execution.id] = process
                
                process.wait()
                
                # Remove from running processes
                if execution.id in task_manager.running_processes:
                    del task_manager.running_processes[execution.id]
                
            execution.end_time = datetime.datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            # Read back some output for the DB record (optional, maybe first 4KB)
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    execution.output = f.read(4096) 
            except:
                execution.output = "See log file."
            
            if process.returncode == 0:
                execution.status = "success"
            else:
                # Check if killed (negative return code usually)
                execution.status = "failed"
                
            db.commit()
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
