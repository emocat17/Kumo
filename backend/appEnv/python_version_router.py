import os
import subprocess
import shutil
import stat
import time
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import get_db, SQLALCHEMY_DATABASE_URL, SessionLocal
from appEnv import models, schemas
import platform
import threading
import sqlite3
import psutil

router = APIRouter()

class PathRequest(BaseModel):
    path: str
    is_conda: Optional[bool] = False 

class OpenTerminalRequest(BaseModel):
    path: str

class CondaCreateRequest(BaseModel):
    version: str
    name: str

# Helper to run command in background
def run_conda_create(command: str, version_id: int):
    # Create a new session for the thread
    db = SessionLocal()
    try:
        print(f"Starting conda creation for ID {version_id} with command: {command}")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        version_record = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        
        if not version_record:
            print(f"Version record {version_id} not found during background task.")
            return

        if process.returncode == 0:
            print(f"Conda environment created successfully.")
            version_record.status = "ready"
            # Optionally verify version here if needed
        else:
            error_msg = stderr.decode()
            print(f"Failed to create conda environment: {error_msg}")
            version_record.status = "error"
            # We could store the error message in a field if we had one
            
        db.commit()
            
    except Exception as e:
        print(f"Error in background conda create: {e}")
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

@router.post("/create-conda-env")
async def create_conda_env(request: CondaCreateRequest, db: Session = Depends(get_db)):
    base_env_path = os.path.abspath(os.path.join(os.getcwd(), "envs"))
    if not os.path.exists(base_env_path):
        os.makedirs(base_env_path)
        
    env_path = os.path.join(base_env_path, request.name)
    
    if os.path.exists(env_path):
        raise HTTPException(status_code=400, detail=f"Environment path already exists: {env_path}")

    command = f"conda create --prefix \"{env_path}\" python={request.version} -y"
    
    if platform.system() == "Windows":
        python_exe = os.path.join(env_path, "python.exe")
    else:
        python_exe = os.path.join(env_path, "bin", "python")

    # Create DB record immediately with "installing" status
    new_version = models.PythonVersion(
        name=request.name,
        version=request.version, # Temporary version, will be accurate after install if we updated it
        path=python_exe,
        status="installing",
        is_conda=True
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    # Start background thread
    thread = threading.Thread(target=run_conda_create, args=(command, new_version.id))
    thread.start()
    
    return {
        "message": "Environment creation started", 
        "env_path": env_path,
        "python_path": python_exe,
        "id": new_version.id
    }

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
        if os.path.abspath(python_exe).startswith(cwd_envs):
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
    return db.query(models.PythonVersion).all()

# Helper to delete in background
def background_delete_version(version_id: int):
    db = SessionLocal()
    try:
        version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        if not version:
            return

        path_to_delete = version.path
        is_conda_env = version.is_conda
        
        if is_conda_env and path_to_delete:
            try:
                env_dir = os.path.dirname(path_to_delete)
                if platform.system() != "Windows" and os.path.basename(env_dir) == "bin":
                    env_dir = os.path.dirname(env_dir)
                
                cwd_envs = os.path.abspath(os.path.join(os.getcwd(), "envs"))
                
                # Safety check
                if os.path.abspath(env_dir).startswith(cwd_envs) and os.path.exists(env_dir):
                    print(f"Deleting managed conda environment: {env_dir}")
                    
                    # 0. Kill any running processes in this env
                    try:
                        print("Scanning for processes to kill...")
                        target_dir_lower = os.path.abspath(env_dir).lower()
                        for proc in psutil.process_iter(['pid', 'name', 'exe']):
                            try:
                                exe_path = proc.info['exe']
                                if exe_path:
                                    # Normalize paths for comparison
                                    exe_path = os.path.abspath(exe_path).lower()
                                    if exe_path.startswith(target_dir_lower):
                                        print(f"Killing process {proc.info['name']} (PID: {proc.info['pid']})")
                                        proc.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                pass
                    except Exception as e:
                        print(f"Error killing processes: {e}")

                    # 1. Try conda remove (WITHOUT --offline because it breaks due to TOS check)
                    # The error 'RuntimeError: EnforceUnusedAdapter called with url' happens when --offline is used
                    # but conda_anaconda_tos plugin still tries to fetch TOS metadata.
                    # So we revert to standard removal but suppress output to avoid noise.
                    command = f"conda remove --prefix \"{env_dir}\" --all -y"
                    print(f"Executing: {command}")
                    process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    
                    if process.returncode != 0:
                        print(f"Conda remove warning: {process.stderr}")
                    else:
                        print("Conda remove successful")

                    # 2. Robust cleanup loop
                    max_retries = 10
                    for i in range(max_retries):
                        if not os.path.exists(env_dir):
                            break
                            
                        print(f"Cleanup attempt {i+1}/{max_retries} for {env_dir}")
                        
                        try:
                            # Try standard python removal first
                            shutil.rmtree(env_dir, onerror=remove_readonly)
                        except Exception as e:
                            print(f"shutil.rmtree failed: {e}")

                        if not os.path.exists(env_dir):
                            break

                        # Fallback to Windows native commands which are more powerful
                        if platform.system() == "Windows":
                            try:
                                print("Attempting Windows force delete...")
                                # 1. Grant full permissions to Everyone
                                subprocess.run(f'icacls "{env_dir}" /grant Everyone:F /T /C /Q', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                
                                # 2. Force delete all files
                                subprocess.run(f'del /f /s /q /a "{env_dir}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                
                                # 3. Force remove directory
                                subprocess.run(f'rmdir /s /q "{env_dir}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            except Exception as e:
                                print(f"Windows force delete failed: {e}")
                                
                        time.sleep(3) # Wait longer for file locks to release
                    
                    # 3. Final check (No renaming)
                    if os.path.exists(env_dir):
                        print(f"Warning: Failed to completely delete {env_dir} after {max_retries} attempts.")

            except Exception as e:
                print(f"Error in background deletion: {e}")
                pass
        
        # Finally delete the record
        # Re-query to ensure we have the latest session state
        version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        if version:
            db.delete(version)
            db.commit()
            print(f"Version {version_id} deleted from DB")

    except Exception as e:
        print(f"Fatal error in background_delete_version: {e}")
    finally:
        db.close()

@router.delete("/{version_id}")
async def delete_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # If it's a conda environment, do it in background
    if version.is_conda:
        version.status = "deleting"
        db.commit()
        
        thread = threading.Thread(target=background_delete_version, args=(version_id,))
        thread.start()
        
        return {"ok": True, "message": "Deletion started in background"}
    else:
        # Simple path registration, delete immediately
        db.delete(version)
        db.commit()
        return {"ok": True}
