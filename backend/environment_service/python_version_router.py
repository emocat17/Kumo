import os
import subprocess
import shutil
import stat
import time
import re
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from core.database import get_db, SQLALCHEMY_DATABASE_URL, SessionLocal
from environment_service import models, schemas
from task_service.models import Task
from audit_service.service import create_audit_log
import platform
import threading
import sqlite3
import psutil
import datetime

router = APIRouter()

class PathRequest(BaseModel):
    path: str
    is_conda: Optional[bool] = False 

class OpenTerminalRequest(BaseModel):
    path: str

class CondaCreateRequest(BaseModel):
    version: str
    name: str

class LogResponse(BaseModel):
    log: str

def clean_ansi(text: str) -> str:
    """Remove ANSI escape sequences and special characters from text"""
    # Remove standard ANSI escape sequences (colors, cursor movement, etc.)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    # Remove backspace characters (退格键)
    text = re.sub(r'[\x08\x7F]+', '', text)
    # Remove carriage return characters that cause duplicate lines
    text = text.replace('\r', '')
    return text

def get_log_path(version_id: int):
    log_dir = os.path.abspath(os.path.join(os.getcwd(), "logs", "install"))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return os.path.join(log_dir, f"install_v{version_id}.log")

def append_log(version_id: int, message: str):
    # Clean ANSI sequences from message
    message = clean_ansi(message)
    
    # Skip empty or whitespace-only lines
    if not message or not message.strip():
        return
    
    log_file = get_log_path(version_id)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            # Split by actual newlines, not by embedded timestamps
            lines = message.split('\n')
            for line in lines:
                line = line.strip()
                # Skip empty lines and progress-only lines
                if line and not _is_progress_only_line(line):
                    f.write(f"[{timestamp}] {line}\n")
    except Exception:
        pass

def _is_progress_only_line(line: str) -> bool:
    """Check if a line is only progress bar characters"""
    # Remove common characters that appear in progress bars
    cleaned = line.replace('|', '').replace('/', '').replace('-', '').replace('\\', '').replace(' ', '')
    # Also remove timestamp-like patterns [YYYY-MM-DD HH:MM:SS]
    import re
    cleaned = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', '', cleaned)
    cleaned = cleaned.strip()
    return len(cleaned) == 0

# Global dictionary to store output buffers for each process
_process_buffers = {}

# Helper to run command in background (modified to accept list for security)
def run_conda_create(command: list, version_id: int):
    """
    Run conda create in a background thread with proper process management.
    Uses communicate() to properly handle conda's output behavior.
    """
    db = SessionLocal()
    import threading
    
    try:
        cmd_str = " ".join(command)
        append_log(version_id, f"Starting conda creation with command: {cmd_str}")
        append_log(version_id, f"Process will run in: {os.getcwd()}")

        # Use subprocess with PIPE
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=os.getcwd()
        )
        
        append_log(version_id, f"Process started with PID: {process.pid}")

        import time
        start_time = time.time()
        
        try:
            # communicate() reads stdout/stderr and waits for process to finish
            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
            return_code = process.returncode
            
            # Log all output
            if stdout:
                for line in stdout.splitlines():
                    if line.strip():
                        append_log(version_id, line.strip())
            
            append_log(version_id, f"Process completed with return code: {return_code}")
                        
        except subprocess.TimeoutExpired:
            append_log(version_id, "Installation timeout (600s), terminating process...")
            process.kill()
            process.wait()
            return_code = -1
            
            version_record = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
            if version_record:
                version_record.status = "error"
                db.commit()
            append_log(version_id, "Process terminated due to timeout")
            return

        # Wait for any remaining output to be captured
        time.sleep(1)

        version_record = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()

        if not version_record:
            append_log(version_id, f"Version record {version_id} not found.")
            return

        if return_code == 0:
            append_log(version_id, "Conda environment created successfully.")
            version_record.status = "ready"
            
            # Verify python executable exists
            if os.path.exists(version_record.path):
                append_log(version_id, f"Python executable verified: {version_record.path}")
            else:
                append_log(version_id, f"Warning: Python executable not found at: {version_record.path}")
                # Try to find it
                env_dir = os.path.dirname(version_record.path)
                if os.path.exists(env_dir):
                    for f in os.listdir(env_dir):
                        if f.startswith('python') and not f.startswith('python3'):
                            append_log(version_id, f"Found alternative python: {f}")
                            
        else:
            append_log(version_id, f"Conda environment creation failed with code {return_code}")
            version_record.status = "error"

        db.commit()
        append_log(version_id, f"Status updated to: {version_record.status}")
            
    except Exception as e:
        append_log(version_id, f"Error in background conda create: {e}")
        import traceback
        append_log(version_id, f"Traceback: {traceback.format_exc()}")
        # Try to update status to error
        try:
            version_record = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
            if version_record:
                version_record.status = "error"
                db.commit()
        except:
            pass
    finally:
        db.close()

# Helper to remove read-only files (fixes Windows deletion issues)
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

# Database Migration Helper (Safe add column)
def ensure_columns():
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(python_versions)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "name" not in columns:
            print("Migrating: Adding 'name' column to python_versions")
            cursor.execute("ALTER TABLE python_versions ADD COLUMN name VARCHAR DEFAULT ''")
            
        if "is_conda" not in columns:
            print("Migrating: Adding 'is_conda' column to python_versions")
            cursor.execute("ALTER TABLE python_versions ADD COLUMN is_conda BOOLEAN DEFAULT 0")

        if "created_at" not in columns:
            print("Migrating: Adding 'created_at' column to python_versions")
            cursor.execute("ALTER TABLE python_versions ADD COLUMN created_at DATETIME")
            cursor.execute("UPDATE python_versions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            
        if "updated_at" not in columns:
            print("Migrating: Adding 'updated_at' column to python_versions")
            cursor.execute("ALTER TABLE python_versions ADD COLUMN updated_at DATETIME")
            cursor.execute("UPDATE python_versions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

        # Double check for NULLs (in case columns existed but were NULL)
        cursor.execute("UPDATE python_versions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        cursor.execute("UPDATE python_versions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

        # Check and Drop Unique Index on version (Fix for duplicate versions)
        cursor.execute("PRAGMA index_list('python_versions')")
        indexes = cursor.fetchall()
        for idx in indexes:
            # idx: (seq, name, unique, origin, partial)
            index_name = idx[1]
            is_unique = idx[2]
            if is_unique:
                cursor.execute(f"PRAGMA index_info('{index_name}')")
                col_info = cursor.fetchall()
                # col_info: (seqno, cid, name)
                if len(col_info) == 1 and col_info[0][2] == 'version':
                    print(f"Migrating: Dropping unique index '{index_name}' on 'version' column")
                    cursor.execute(f"DROP INDEX {index_name}")

        conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")
    finally:
        conn.close()

ensure_columns()

import json

# Helper to get default conda envs directory
def get_default_conda_env_dir():
    try:
        # Run conda info --json to get envs_dirs
        result = subprocess.run(["conda", "info", "--json"], capture_output=True, text=True)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            if "envs_dirs" in info and len(info["envs_dirs"]) > 0:
                return info["envs_dirs"][0]
    except Exception as e:
        print(f"Error getting conda info: {e}")
    
    # Fallback: assume standard location relative to conda executable if possible, 
    # or just return None and let the code fail gracefully or use a default.
    return None

@router.post("/create-conda-env")
async def create_conda_env(request: CondaCreateRequest, db: Session = Depends(get_db)):
    # Always use explicit path to ensure environment is created in the mapped volume
    # This prevents environment loss after container restart
    base_env_path = os.path.abspath(os.path.join(os.getcwd(), "envs"))

    # Ensure the envs directory exists
    if not os.path.exists(base_env_path):
        os.makedirs(base_env_path)

    # Sanitize environment name to prevent command injection
    # Only allow alphanumeric, dash, underscore
    safe_name = "".join(c for c in request.name if c.isalnum() or c in '-_')
    if not safe_name or safe_name != request.name:
        raise HTTPException(status_code=400, detail="Invalid environment name. Use only letters, numbers, dash and underscore.")

    # Validate version format (basic check)
    safe_version = "".join(c for c in request.version if c.isdigit() or c in '.-')
    if not safe_version:
        raise HTTPException(status_code=400, detail="Invalid Python version format")

    env_path = os.path.join(base_env_path, safe_name)

    # Check if exists - if exists but failed before, try to clean up
    if os.path.exists(env_path):
        # Check if environment is in DB with error/installing status - if so, allow cleanup and retry
        existing = db.query(models.PythonVersion).filter(models.PythonVersion.name == safe_name).first()
        if existing and existing.status in ["installing", "error"]:
            append_log(existing.id if existing else 0, f"Found residual directory from previous failed installation. Cleaning up...")
            # Mark for deletion in background, then proceed
            # For now, let's try to delete it directly
            try:
                import shutil as sh
                import subprocess as sp
                result = sp.run(['rm', '-rf', env_path], capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    append_log(existing.id if existing else 0, f"Successfully cleaned up residual directory: {env_path}")
                else:
                    append_log(existing.id if existing else 0, f"Failed to clean residual directory: {result.stderr}")
                    # Try harder with conda clean
                    sp.run(['conda', 'clean', '-afy'], capture_output=True, text=True, timeout=60)
                    # Try rm again
                    result2 = sp.run(['rm', '-rf', env_path], capture_output=True, text=True, timeout=30)
                    if result2.returncode != 0:
                        raise HTTPException(status_code=400, detail=f"Cannot clean residual directory: {env_path}. Please delete manually.")
            except Exception as clean_err:
                append_log(existing.id if existing else 0, f"Error during cleanup: {clean_err}")
                raise HTTPException(status_code=400, detail=f"Failed to clean residual directory: {clean_err}")
        elif existing and existing.status == "ready":
            raise HTTPException(status_code=400, detail=f"Environment path already exists: {env_path}")
        else:
            # No DB record but directory exists - likely leftover, try to clean
            try:
                import shutil as sh
                import subprocess as sp
                result = sp.run(['rm', '-rf', env_path], capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    raise HTTPException(status_code=400, detail=f"Cannot clean unknown directory: {env_path}. Please delete manually.")
            except Exception as clean_err:
                raise HTTPException(status_code=400, detail=f"Failed to clean unknown directory: {clean_err}")

    # Always use --prefix to ensure environment is created in the mapped volume
    # This ensures persistence across container restarts
    # Use -q (quiet) to reduce output and speed up by not rendering progress bars
    
    # First, ensure conda channels are configured correctly (fix potential URL format issues)
    try:
        import subprocess as sp
        # Set correct channel URLs (with proper https:// prefix)
        sp.run(["conda", "config", "--add", "channels", "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge"], 
               capture_output=True, timeout=30)
        sp.run(["conda", "config", "--add", "channels", "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free"], 
               capture_output=True, timeout=30)
        sp.run(["conda", "config", "--add", "channels", "https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main"], 
               capture_output=True, timeout=30)
        sp.run(["conda", "config", "--set", "show_channel_urls", "yes"], 
               capture_output=True, timeout=30)
    except Exception as e:
        append_log(0, f"Warning: Failed to configure conda channels: {e}")
    
    command = [
        "conda", "create", "--prefix", env_path, 
        f"python={safe_version}", "-y", "-q"
    ]

    if platform.system() == "Windows":
        python_exe = os.path.join(env_path, "python.exe")
    else:
        python_exe = os.path.join(env_path, "bin", "python")

    # Create DB record immediately with "installing" status
    new_version = models.PythonVersion(
        name=safe_name,
        version=safe_version,
        path=python_exe,
        status="installing",
        is_conda=True
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    log_file = get_log_path(new_version.id)
    if os.path.exists(log_file):
        os.remove(log_file)

    # Start background thread
    thread = threading.Thread(target=run_conda_create, args=(command, new_version.id))
    thread.start()
    
    return {
        "message": "Environment creation started", 
        "env_path": env_path,
        "python_path": python_exe,
        "id": new_version.id
    }

@router.get("/{version_id}/logs", response_model=LogResponse)
async def get_install_logs(version_id: int):
    log_file = get_log_path(version_id)
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
            return {"log": content}
        except Exception as e:
            return {"log": f"Error reading log: {e}"}
    else:
        return {"log": "No installation logs found."}

@router.post("/open-terminal")
async def open_terminal(request: OpenTerminalRequest):
    path = request.path.strip()
    # Only check path existence if status is ready (handled by frontend mostly, but good to know)
    # But for terminal opening, we need the path to exist.
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"Executable not found: {path}")
    
    cwd = os.path.dirname(path)
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(f'start cmd /K "cd /d {cwd} && echo Environment: {path} && python --version"', shell=True)
        elif system == "Darwin":
            script = f'''
            tell application "Terminal"
                do script "cd '{cwd}'; echo 'Environment: {path}'; python --version"
                activate
            end tell
            '''
            subprocess.run(["osascript", "-e", script])
        elif system == "Linux":
            terminals = ["gnome-terminal", "xterm", "konsole", "xfce4-terminal"]
            opened = False
            for term in terminals:
                try:
                    if term == "gnome-terminal":
                        subprocess.Popen([term, "--", "bash", "-c", f"cd '{cwd}'; echo 'Environment: {path}'; python --version; exec bash"])
                    else:
                        subprocess.Popen([term, "-e", f"bash -c \"cd '{cwd}'; echo 'Environment: {path}'; python --version; exec bash\""])
                    opened = True
                    break
                except FileNotFoundError:
                    continue
            
            if not opened:
                raise HTTPException(status_code=500, detail="No supported terminal emulator found")
        else:
             raise HTTPException(status_code=500, detail=f"Unsupported operating system: {system}")
             
        return {"ok": True, "message": "Terminal opened"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open terminal: {str(e)}")


@router.post("/add-by-path", response_model=schemas.PythonVersion)
async def add_python_version(request: PathRequest, db: Session = Depends(get_db)):
    path = request.path.strip()
    
    if os.path.isdir(path):
        python_exe = os.path.join(path, "python.exe")
    else:
        python_exe = path

    if not os.path.exists(python_exe):
        raise HTTPException(status_code=400, detail=f"Python executable not found at: {python_exe}")

    try:
        result = subprocess.run([python_exe, "--version"], capture_output=True, text=True)
        if result.returncode != 0:
             raise Exception("Failed to run python --version")

        output = result.stdout.strip() or result.stderr.strip()
        if "Python" in output:
             version_str = output.split(" ")[1]
        else:
             version_str = output

        existing = db.query(models.PythonVersion).filter(models.PythonVersion.version == version_str).first()
        
        dir_path = os.path.dirname(python_exe)
        folder_name = os.path.basename(dir_path)
        
        if folder_name.lower() == "scripts": 
             env_name = os.path.basename(os.path.dirname(dir_path))
        elif folder_name.lower() == "bin":
             env_name = os.path.basename(os.path.dirname(dir_path))
        else:
             env_name = folder_name
             
        is_conda = request.is_conda
        cwd_envs = os.path.abspath(os.path.join(os.getcwd(), "envs"))
        default_conda_dir = get_default_conda_env_dir()
        
        abs_exe = os.path.abspath(python_exe)
        if abs_exe.startswith(cwd_envs):
            is_conda = True
        elif default_conda_dir and abs_exe.startswith(os.path.abspath(default_conda_dir)):
            is_conda = True
        
        if existing:
            existing.path = python_exe
            existing.name = env_name
            existing.is_conda = is_conda
            # Reset status to ready if it was installing/error
            existing.status = "ready"
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_version = models.PythonVersion(
                name=env_name,
                version=version_str,
                path=python_exe,
                status="ready",
                is_conda=is_conda
            )
            db.add(new_version)
            db.commit()
            db.refresh(new_version)
            return new_version

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying python: {str(e)}")

@router.get("", response_model=List[schemas.PythonVersion])
async def list_versions(db: Session = Depends(get_db)):
    versions = db.query(models.PythonVersion).all()
    
    # Check for usage in Tasks
    tasks = db.query(Task).all()
    
    usage_map = {}
    for task in tasks:
        if task.env_id:
            if task.env_id not in usage_map:
                usage_map[task.env_id] = []
            usage_map[task.env_id].append(task.name)
    
    for v in versions:
        used_tasks = usage_map.get(v.id, [])
        v.is_in_use = len(used_tasks) > 0
        v.used_by_tasks = used_tasks
        
    return versions

# Helper to delete in background
def background_delete_version(version_id: int):
    """
    后台删除环境线程，支持超时检测
    超时时间默认 5 分钟（300秒）
    """
    db = SessionLocal()
    timeout_seconds = 300  # 5 minutes timeout
    
    try:
        version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        if not version:
            return

        start_time = time.time()
        path_to_delete = version.path
        is_conda_env = version.is_conda
        env_name = version.name

        def check_timeout():
            """检查是否超时"""
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                append_log(version_id, f"Delete operation timed out after {elapsed:.1f} seconds")
                return True
            return False

        append_log(version_id, f"Starting deletion for: {path_to_delete}")
        append_log(version_id, f"Timeout set to {timeout_seconds} seconds")

        if is_conda_env and path_to_delete:
            try:
                env_dir = os.path.dirname(path_to_delete)
                if platform.system() != "Windows" and os.path.basename(env_dir) == "bin":
                    env_dir = os.path.dirname(env_dir)

                append_log(version_id, f"Environment directory: {env_dir}")

                # Check if directory exists first
                if not os.path.exists(env_dir):
                    append_log(version_id, "Environment directory does not exist, skipping file deletion")
                else:
                    # 0. Kill any running processes in this env (simplified)
                    try:
                        append_log(version_id, "Checking for running processes...")
                        target_dir_lower = os.path.abspath(env_dir).lower()
                        killed_any = False
                        for proc in psutil.process_iter(['pid', 'name', 'exe']):
                            try:
                                exe_path = proc.info['exe']
                                if exe_path:
                                    exe_path = os.path.abspath(exe_path).lower()
                                    if exe_path.startswith(target_dir_lower):
                                        append_log(version_id, f"Killing process: {proc.info['name']} (PID: {proc.info['pid']})")
                                        proc.kill()
                                        killed_any = True
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                pass
                        if not killed_any:
                            append_log(version_id, "No running processes found in environment")
                    except Exception as e:
                        append_log(version_id, f"Warning: Process scan error: {e}")

                    # Skip conda remove - it's slow and we will delete the directory anyway
                    # Just verify the environment exists before deletion
                    append_log(version_id, "Skipping conda remove, proceeding with directory deletion...")

                    # Use system command for faster and more reliable deletion in containers
                    # This is more reliable than shutil.rmtree for locked files
                    env_deleted = False
                    try:
                        # Try using rm -rf first (works best in Linux containers)
                        import subprocess as sp
                        result = sp.run(
                            ['rm', '-rf', env_dir],
                            capture_output=True,
                            text=True,
                            timeout=60  # 60 second timeout
                        )
                        if result.returncode == 0:
                            append_log(version_id, "Directory deleted successfully via rm -rf")
                            env_deleted = True
                        else:
                            append_log(version_id, f"rm -rf failed: {result.stderr}")
                    except sp.TimeoutExpired:
                        append_log(version_id, "Delete command timed out after 60 seconds")
                    except Exception as e:
                        append_log(version_id, f"Error using system delete: {e}")

                    # Fallback to Python shutil if system command failed
                    if not env_deleted and os.path.exists(env_dir):
                        append_log(version_id, "Trying shutil.rmtree as fallback...")
                        max_retries = 2
                        for i in range(max_retries):
                            if not os.path.exists(env_dir):
                                append_log(version_id, "Directory already deleted")
                                env_deleted = True
                                break

                            append_log(version_id, f"Cleanup attempt {i+1}/{max_retries}...")

                            try:
                                # Try with error handler
                                def handle_remove_readonly(func, path, exc):
                                    import stat
                                    os.chmod(path, stat.S_IWRITE)
                                    func(path)
                                
                                shutil.rmtree(env_dir, onerror=handle_remove_readonly)
                            except Exception as e:
                                append_log(version_id, f"shutil.rmtree error: {e}")

                            if not os.path.exists(env_dir):
                                append_log(version_id, "Directory deleted successfully")
                                env_deleted = True
                                break

                            time.sleep(1)

                    # Final check
                    if os.path.exists(env_dir):
                        append_log(version_id, f"Warning: Failed to delete {env_dir}, continuing anyway")
                    else:
                        append_log(version_id, "Cleanup completed")

            except Exception as e:
                append_log(version_id, f"Error in background deletion: {e}")

        # Check timeout before final cleanup
        if check_timeout():
            append_log(version_id, "Operation timed out, marking as error")
            version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
            if version:
                version.status = "error"
                db.commit()
            return

        # Finally delete the record
        version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        if version:
            db.delete(version)
            db.commit()
            append_log(version_id, "Database record deleted")

    except Exception as e:
        print(f"Fatal error in background_delete_version: {e}")
        try:
            # Try to mark as error
            version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
            if version:
                version.status = "error"
                db.commit()
        except:
            pass
    finally:
        db.close()

@router.delete("/{version_id}")
async def delete_version(version_id: int, req: Request, db: Session = Depends(get_db)):
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Check if used by any tasks
    used_tasks = db.query(Task).filter(Task.env_id == version_id).first()
    if used_tasks:
        raise HTTPException(status_code=400, detail=f"Cannot delete environment '{version.name}': It is used by task '{used_tasks.name}'")

    # Audit Log
    create_audit_log(
        db=db,
        operation_type="DELETE",
        target_type="ENVIRONMENT",
        target_id=str(version.id),
        target_name=version.name,
        details=f"Deleted environment '{version.name}'",
        operator_ip=req.client.host
    )
    
    # Check if path is in managed envs directory
    # If so, treat it as a managed environment that needs file deletion
    is_managed_path = False
    if version.path:
        try:
            cwd_envs = os.path.abspath(os.path.join(os.getcwd(), "envs"))
            abs_path = os.path.abspath(version.path)
            if abs_path.startswith(cwd_envs):
                is_managed_path = True
        except:
            pass
    
    # If it's a conda environment OR it's in our managed directory, do it in background
    if version.is_conda or is_managed_path:
        version.status = "deleting"
        # Ensure is_conda is True so background task processes it
        if not version.is_conda:
            version.is_conda = True
            
        # Audit Log
        create_audit_log(
            db=db,
            operation_type="DELETE",
            target_type="ENVIRONMENT",
            target_id=str(version.id),
            target_name=version.name,
            details=f"Started deletion of environment '{version.name}'"
        )
            
        db.commit()
        
        thread = threading.Thread(target=background_delete_version, args=(version_id,))
        thread.start()
        
        return {"ok": True, "message": "Deletion started in background"}
    else:
        # Simple path registration, delete immediately
        db.delete(version)
        db.commit()
        return {"ok": True}


@router.post("/{version_id}/reset-status")
async def reset_version_status(version_id: int, req: Request, db: Session = Depends(get_db)):
    """
    重置环境状态，用于修复卡在 'deleting' 等异常状态的环境
    """
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    old_status = version.status
    new_status = "error"  # 默认重置为错误状态
    
    version.status = new_status
    db.commit()
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="ENVIRONMENT",
        target_id=str(version.id),
        target_name=version.name,
        details=f"Reset status from '{old_status}' to '{new_status}'",
        operator_ip=req.client.host
    )
    
    return {"ok": True, "message": f"Status reset from '{old_status}' to '{new_status}'"}


@router.post("/{version_id}/force-delete")
async def force_delete_version(version_id: int, req: Request, db: Session = Depends(get_db)):
    """
    强制删除环境，忽略任务使用检查并清理相关文件
    """
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # 检查是否有任务使用此环境，并解除关联
    tasks = db.query(Task).filter(Task.env_id == version_id).all()
    for task in tasks:
        task.env_id = None
        append_log(version_id, f"Unlinked task: {task.name}")
    
    env_name = version.name
    env_path = version.path
    
    # 删除数据库记录
    db.delete(version)
    db.commit()
    
    # 尝试删除物理目录（如果存在）
    if env_path:
        try:
            env_dir = os.path.dirname(env_path)
            if platform.system() != "Windows" and os.path.basename(env_dir) == "bin":
                env_dir = os.path.dirname(env_dir)
            
            if os.path.exists(env_dir):
                append_log(version_id, f"Force deleting directory: {env_dir}")
                result = subprocess.run(
                    ['rm', '-rf', env_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    append_log(version_id, "Directory force deleted successfully")
                else:
                    append_log(version_id, f"Force delete warning: {result.stderr}")
            else:
                append_log(version_id, "Directory does not exist, skipping")
        except Exception as e:
            append_log(version_id, f"Force delete error: {e}")
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="FORCE_DELETE",
        target_type="ENVIRONMENT",
        target_id=str(version_id),
        target_name=env_name,
        details=f"Force deleted environment '{env_name}'",
        operator_ip=req.client.host
    )
    
    return {"ok": True, "message": f"Environment '{env_name}' force deleted"}


@router.post("/cleanup-cache")
async def cleanup_conda_cache(req: Request, db: Session = Depends(get_db)):
    """清理 Conda 缓存，解决卡住问题"""
    append_log(0, "Starting conda cache cleanup...")
    
    try:
        # Run conda clean
        result = subprocess.run(
            ["conda", "clean", "-afy"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Also clean pip cache
        pip_result = subprocess.run(
            ["pip", "cache", "purge"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Clean any stale lock files in envs directory
        envs_dir = os.path.abspath(os.path.join(os.getcwd(), "envs"))
        if os.path.exists(envs_dir):
            cleaned_count = 0
            for item in os.listdir(envs_dir):
                item_path = os.path.join(envs_dir, item)
                if os.path.isdir(item_path):
                    pkgs_dir = os.path.join(item_path, "pkgs")
                    if os.path.exists(pkgs_dir):
                        try:
                            import shutil
                            shutil.rmtree(pkgs_dir)
                            cleaned_count += 1
                        except:
                            pass
            append_log(0, f"Cleaned {cleaned_count} package caches")
        
        append_log(0, f"Conda cache cleanup completed. Return code: {result.returncode}")
        
        create_audit_log(
            db=db,
            operation_type="CLEANUP",
            target_type="ENVIRONMENT",
            target_id="cache",
            target_name="conda_cache",
            details="Cleaned conda and pip cache",
            operator_ip=req.client.host
        )
        
        return {
            "ok": True, 
            "message": "Cache cleaned successfully",
            "conda_output": result.stdout[:1000] if result.stdout else "",
            "pip_output": pip_result.stdout if pip_result.stdout else ""
        }
    except subprocess.TimeoutExpired:
        append_log(0, "Cache cleanup timed out")
        return {"ok": False, "message": "Cache cleanup timed out"}
    except Exception as e:
        append_log(0, f"Cache cleanup error: {e}")
        return {"ok": False, "message": f"Error: {str(e)}"}

@router.post("/cleanup-residual")
async def cleanup_residual_environments(req: Request, db: Session = Depends(get_db)):
    """清理所有残留的环境目录（数据库中不存在但文件系统存在的）"""
    envs_dir = os.path.abspath(os.path.join(os.getcwd(), "envs"))
    
    if not os.path.exists(envs_dir):
        return {"ok": True, "message": "Envs directory does not exist", "cleaned": []}
    
    registered_envs = db.query(models.PythonVersion).all()
    registered_names = {e.name for e in registered_envs}
    
    cleaned = []
    errors = []
    
    for item in os.listdir(envs_dir):
        item_path = os.path.join(envs_dir, item)
        
        if not os.path.isdir(item_path):
            continue
            
        if item.startswith('.') or item in ['__pycache__', 'conda-meta']:
            continue
            
        if item not in registered_names:
            try:
                import subprocess as sp
                result = sp.run(['rm', '-rf', item_path], capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    cleaned.append(item)
                    append_log(0, f"Cleaned residual directory: {item}")
                else:
                    errors.append(f"{item}: {result.stderr}")
            except Exception as e:
                errors.append(f"{item}: {str(e)}")
    
    create_audit_log(
        db=db,
        operation_type="CLEANUP",
        target_type="ENVIRONMENT",
        target_id="residual",
        target_name="residual_envs",
        details=f"Cleaned {len(cleaned)} residual environments: {', '.join(cleaned)}",
        operator_ip=req.client.host
    )
    
    return {
        "ok": True, 
        "message": f"Found {len(cleaned)} residual directories",
        "cleaned": cleaned,
        "errors": errors
    }

@router.post("/reset-stuck-env/{version_id}")
async def reset_stuck_environment(version_id: int, req: Request, db: Session = Depends(get_db)):
    """重置卡住的环境状态，允许重新创建"""
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    if version.status not in ["installing", "error"]:
        raise HTTPException(status_code=400, detail=f"Cannot reset environment with status: {version.status}")
    
    env_path = os.path.dirname(version.path)
    if os.path.exists(env_path):
        try:
            import subprocess as sp
            result = sp.run(['rm', '-rf', env_path], capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                append_log(version_id, f"Warning: Could not clean env directory: {result.stderr}")
        except Exception as e:
            append_log(version_id, f"Warning: Error cleaning env directory: {e}")
    
    old_status = version.status
    version.status = "error"
    version.updated_at = datetime.datetime.now()
    db.commit()
    
    append_log(version_id, f"Reset environment status from '{old_status}' to 'error'")
    
    create_audit_log(
        db=db,
        operation_type="RESET",
        target_type="ENVIRONMENT",
        target_id=str(version.id),
        target_name=version.name,
        details=f"Reset stuck environment (was: {old_status})",
        operator_ip=req.client.host
    )
    
    return {
        "ok": True, 
        "message": f"Environment reset. You can now try to recreate it.",
        "status": version.status
    }

@router.post("/cleanup-orphaned")
async def cleanup_orphaned_records(req: Request, db: Session = Depends(get_db)):
    """清理失效的数据库记录（数据库中存在但文件系统目录不存在的环境）"""
    base_env_path = os.path.abspath(os.path.join(os.getcwd(), "envs"))
    
    all_versions = db.query(models.PythonVersion).all()
    
    cleaned = []
    errors = []
    
    for version in all_versions:
        # Check if the directory exists
        env_dir = os.path.dirname(version.path)  # Get the directory, not the python executable
        
        if not os.path.exists(env_dir):
            # Directory doesn't exist - this is an orphaned record
            try:
                # Delete the DB record
                version_name = version.name
                version_id = version.id
                db.delete(version)
                db.commit()
                cleaned.append({
                    "id": version_id,
                    "name": version_name,
                    "path": env_dir,
                    "status": version.status
                })
                append_log(version_id, f"Cleaned orphaned DB record: {version_name} (path: {env_dir} not found)")
            except Exception as e:
                errors.append(f"{version.name}: {str(e)}")
                db.rollback()
    
    create_audit_log(
        db=db,
        operation_type="CLEANUP",
        target_type="ENVIRONMENT",
        target_id="orphaned",
        target_name="orphaned_records",
        details=f"Cleaned {len(cleaned)} orphaned DB records: {', '.join([c['name'] for c in cleaned])}",
        operator_ip=req.client.host
    )
    
    return {
        "ok": True,
        "message": f"Found {len(cleaned)} orphaned records and cleaned them",
        "cleaned": cleaned,
        "errors": errors
    }
