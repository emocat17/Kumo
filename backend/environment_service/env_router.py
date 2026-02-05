import os
import subprocess
import platform
import threading
import time
import datetime
from sqlalchemy.sql import func
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from core.database import get_db, SessionLocal
from environment_service import models, schemas
from system_service import models as system_models
from audit_service.service import create_audit_log

router = APIRouter()

# --- Schemas for Package Management ---
class PackageInfo(BaseModel):
    name: str
    version: str

class PackageInstallRequest(BaseModel):
    packages: str # space separated or newline separated
    is_conda: bool = False

class LogResponse(BaseModel):
    log: str

# --- Helpers ---

def get_log_path(version_id: int):
    """Returns path to the install log file for this version"""
    log_dir = os.path.abspath(os.path.join(os.getcwd(), "logs", "install"))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return os.path.join(log_dir, f"install_v{version_id}.log")

def append_log(version_id: int, message: str):
    """Appends message to the log file"""
    log_file = get_log_path(version_id)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error writing log: {e}")

def run_install_background(version_id: int, cmd: list):
    db = SessionLocal()
    try:
        version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
        if not version:
            return

        # Log the command (join if it's a list for display)
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        append_log(version_id, f"Starting installation with command: {cmd_str}")
        
        # Prepare environment with Proxy support
        env_vars = os.environ.copy()
        try:
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
                    append_log(version_id, f"Using Proxy: {p_url}")
        except Exception as e:
            append_log(version_id, f"Warning: Failed to inject proxy settings: {e}")

        # Use shell=False for list to avoid redirection issues
        process = subprocess.Popen(
            cmd, 
            shell=False,
            env=env_vars,
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            encoding='utf-8', 
            errors='replace'
        )
        
        # Stream output to log file
        for line in process.stdout:
            append_log(version_id, line.strip())
            
        process.wait()
        
        if process.returncode == 0:
            append_log(version_id, "Installation completed successfully.")
            # Reset status to ready and update timestamp
            version.status = "ready"
            version.updated_at = datetime.datetime.now()
        else:
            append_log(version_id, f"Installation failed with return code {process.returncode}")
            version.status = "error" 
            version.updated_at = datetime.datetime.now()
            
        db.commit()
        
    except Exception as e:
        append_log(version_id, f"Fatal error during installation: {str(e)}")
        try:
             version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
             if version:
                 version.status = "error"
                 db.commit()
        except:
            pass
    finally:
        db.close()


def get_python_executable(version: models.PythonVersion):
    """Returns the path to python executable or conda prefix based on version type"""
    return version.path

# --- Endpoints ---

@router.get("/{version_id}/packages", response_model=List[PackageInfo])
async def list_packages(version_id: int, db: Session = Depends(get_db)):
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python version not found")

    packages = []
    
    # Use pip list --format=json
    # We prefer 'python -m pip' to ensure we use the right environment
    cmd = [version.path, "-m", "pip", "list", "--format=json"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            try:
                data = json.loads(result.stdout)
                for item in data:
                    packages.append(PackageInfo(name=item['name'], version=item['version']))
            except:
                pass
        else:
             print(f"pip list failed: {result.stderr}")
             # Fallback to conda list if it's a conda env?
             if version.is_conda:
                 # Try conda list
                 env_dir = os.path.dirname(version.path)
                 # If bin/python or Scripts/python, go up
                 if os.path.basename(env_dir).lower() in ['bin', 'scripts']:
                     env_dir = os.path.dirname(env_dir)
                     
                 cmd_conda = f"conda list -p \"{env_dir}\" --json"
                 res_conda = subprocess.run(cmd_conda, shell=True, capture_output=True, text=True)
                 if res_conda.returncode == 0:
                     import json
                     try:
                         data = json.loads(res_conda.stdout)
                         packages = [] # Reset
                         for item in data:
                             packages.append(PackageInfo(name=item['name'], version=item['version']))
                     except:
                         pass
    except Exception as e:
        print(f"Error listing packages: {e}")
        
    return packages

@router.post("/{version_id}/packages")
async def install_packages(version_id: int, request: PackageInstallRequest, req: Request, db: Session = Depends(get_db)):
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python version not found")

    # Split by whitespace to get individual requirements
    pkgs_list = request.packages.replace("\n", " ").split()
    pkgs_list = [p.strip() for p in pkgs_list if p.strip()]
    
    if not pkgs_list:
         return {"message": "No packages specified"}
    
    # Construct command as a list to avoid shell injection/redirection issues
    # Note: run_install_background needs to handle list vs string properly
    
    cmd_list = []

    if request.is_conda and version.is_conda:
        # Use conda install
        env_dir = os.path.dirname(version.path)
        if os.path.basename(env_dir).lower() in ['bin', 'scripts']:
             env_dir = os.path.dirname(env_dir)
             
        # Prefer using prefix for safety, but if it's named env we could use -n. 
        # Using -p is safer for explicit path.
        # We must use list to avoid shell injection
        cmd_list = ["conda", "install", "-p", env_dir, "-y"] + pkgs_list
    else:
        # Use pip install
        # version.path is the python executable
        cmd_list = [version.path, "-m", "pip", "install"]
        
        # Check for PyPI mirror
        mirror_config = db.query(system_models.SystemConfig).filter(system_models.SystemConfig.key == "pypi_mirror").first()
        if mirror_config and mirror_config.value:
            cmd_list.extend(["-i", mirror_config.value])
            
        cmd_list += pkgs_list
    
    # Update status to "installing" (which maps to "配置中" in frontend)
    # Update updated_at explicitly to match log time logic
    # Use datetime.datetime.now() to ensure consistency with Python log time, instead of DB server time
    version.status = "installing"
    version.updated_at = datetime.datetime.now()
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="INSTALL_PACKAGE",
        target_type="ENVIRONMENT",
        target_id=str(version.id),
        target_name=version.name,
        details=f"Started installation of packages: {', '.join(pkgs_list)}",
        operator_ip=req.client.host
    )

    db.commit()
    
    # Clear old log
    log_file = get_log_path(version_id)
    if os.path.exists(log_file):
        os.remove(log_file)
        
    # Start background task
    thread = threading.Thread(target=run_install_background, args=(version_id, cmd_list))
    thread.start()
    
    return {"message": "Installation started in background"}

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

@router.delete("/{version_id}/packages/{package_name}")
async def uninstall_package(version_id: int, package_name: str, req: Request, db: Session = Depends(get_db)):
    version = db.query(models.PythonVersion).filter(models.PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python version not found")

    # Try pip uninstall first
    cmd = f"\"{version.path}\" -m pip uninstall {package_name} -y"
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if process.returncode != 0:
         # If failed, and it's conda, try conda remove
         if version.is_conda:
             env_dir = os.path.dirname(version.path)
             if os.path.basename(env_dir).lower() in ['bin', 'scripts']:
                 env_dir = os.path.dirname(env_dir)
             
             cmd_conda = f"conda remove -p \"{env_dir}\" {package_name} -y"
             proc_conda = subprocess.run(cmd_conda, shell=True, capture_output=True, text=True)
             if proc_conda.returncode != 0:
                 raise HTTPException(status_code=500, detail=f"Uninstall failed: {proc_conda.stderr}")
         else:
             raise HTTPException(status_code=500, detail=f"Uninstall failed: {process.stderr}")
    
    # Audit Log
    create_audit_log(
        db=db,
        operation_type="UNINSTALL_PACKAGE",
        target_type="ENVIRONMENT",
        target_id=str(version.id),
        target_name=version.name,
        details=f"Uninstalled package: {package_name}",
        operator_ip=req.client.host
    )
             
    return {"message": "Uninstallation successful"}

# Reuse the same model for listing environments (which are actually versions now)
@router.get("", response_model=List[schemas.PythonVersion])
async def list_environments(db: Session = Depends(get_db)):
    # Just return the versions, as they are the "environments" now
    return db.query(models.PythonVersion).all()
