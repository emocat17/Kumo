import os
import subprocess
import shutil
import stat
import time
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

def get_log_path(version_id: int):
    log_dir = os.path.abspath(os.path.join(os.getcwd(), "logs", "install"))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return os.path.join(log_dir, f"install_v{version_id}.log")

def append_log(version_id: int, message: str):
    log_file = get_log_path(version_id)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

# Helper to run command in background (modified to accept list for security)
def run_conda_create(command: list, version_id: int):
    # Create a new session for the thread
    db = SessionLocal()
    try:
        cmd_str = " ".join(command)
        append_log(version_id, f"Starting conda creation with command: {cmd_str}")

        # Use communicate() to properly wait for process to complete
        # and read all output from both stdout and stderr
        process = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        # Read all output using communicate() - this ensures we get all output
        # and the process fully completes before we proceed
        stdout, _ = process.communicate()

        # Write output to log file
        if stdout:
            for line in stdout.splitlines():
                append_log(version_id, line.strip())

        # Now check return code
        return_code = process.returncode

        version_record = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()

        if not version_record:
            append_log(version_id, f"Version record {version_id} not found.")
            return

        if return_code == 0:
            append_log(version_id, "Conda environment created successfully.")
            version_record.status = "ready"
        else:
            append_log(version_id, f"Conda environment creation failed with code {return_code}")
            version_record.status = "error"

        db.commit()
            
    except Exception as e:
        append_log(version_id, f"Error in background conda create: {e}")
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

    # Check if exists (simple check, conda will also check)
    if os.path.exists(env_path):
        raise HTTPException(status_code=400, detail=f"Environment path already exists: {env_path}")

    # Always use --prefix to ensure environment is created in the mapped volume
    # This ensures persistence across container restarts
    command = ["conda", "create", "--prefix", env_path, f"python={safe_version}", "-y"]

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
    db = SessionLocal()
    try:
        version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        if not version:
            return

        path_to_delete = version.path
        is_conda_env = version.is_conda
        env_name = version.name

        append_log(version_id, f"Starting deletion for: {path_to_delete}")

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

                    # 1. Try to rename folder first (Windows trick to handle locked files)
                    try:
                        timestamp = int(time.time())
                        trash_dir = f"{env_dir}_trash_{timestamp}"
                        append_log(version_id, f"Attempting to rename: {env_dir}")
                        os.rename(env_dir, trash_dir)
                        env_dir = trash_dir
                        append_log(version_id, "Rename successful")
                    except Exception as e:
                        append_log(version_id, f"Rename failed (continuing with original path): {e}")
                        # Continue with original path

                    # 2. Delete directory with reduced retry count
                    max_retries = 3  # Reduced from 10
                    for i in range(max_retries):
                        if not os.path.exists(env_dir):
                            append_log(version_id, "Directory already deleted")
                            break

                        append_log(version_id, f"Cleanup attempt {i+1}/{max_retries}...")

                        try:
                            shutil.rmtree(env_dir, onerror=remove_readonly)
                        except Exception as e:
                            append_log(version_id, f"shutil.rmtree error: {e}")

                        if not os.path.exists(env_dir):
                            append_log(version_id, "Directory deleted successfully")
                            break

                        # Short wait for file locks to release
                        time.sleep(2)

                    # 3. Final check
                    if os.path.exists(env_dir):
                        append_log(version_id, f"Warning: Failed to delete {env_dir} after {max_retries} attempts")
                    else:
                        append_log(version_id, "Cleanup completed")

            except Exception as e:
                append_log(version_id, f"Error in background deletion: {e}")

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
