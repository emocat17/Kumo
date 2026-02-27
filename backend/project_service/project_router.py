import os
import shutil
import zipfile
import py7zr
import rarfile
import platform
import subprocess
import time
import stat
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from project_service import models, schemas
from task_service.models import Task
import datetime
from pydantic import BaseModel
from audit_service.service import create_audit_log

router = APIRouter()

PROJECTS_DIR = os.path.abspath(os.path.join(os.getcwd(), "projects"))

if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

# Helper to run DB migration for output_dir
def ensure_project_columns():
    db_path = "backend/data/TaskManage.db" # Hardcoded relative path, should be config based
    # Better to rely on SQLALCHEMY_DATABASE_URL but that's in app.database
    # Let's import it
    from core.database import SQLALCHEMY_DATABASE_URL
    import sqlite3
    
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "output_dir" not in columns:
            print("Migrating: Adding 'output_dir' column to projects")
            cursor.execute("ALTER TABLE projects ADD COLUMN output_dir VARCHAR DEFAULT NULL")
            
        conn.commit()
    except Exception as e:
        print(f"Project migration warning: {e}")
    finally:
        conn.close()

ensure_project_columns()

def get_archive_extension(filename: str):
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lower()

def extract_archive(archive_path: str, ext: str, dest_dir: str):
    if ext == ".zip":
        if not zipfile.is_zipfile(archive_path):
            raise Exception("Uploaded file is not a valid zip file")
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        return
    if ext == ".7z":
        if not py7zr.is_7zfile(archive_path):
            raise Exception("Uploaded file is not a valid 7z file")
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            archive.extractall(dest_dir)
        return
    if ext == ".rar":
        if not rarfile.is_rarfile(archive_path):
            raise Exception("Uploaded file is not a valid rar file")
        with rarfile.RarFile(archive_path, 'r') as archive:
            archive.extractall(dest_dir)
        return
    raise Exception("Unsupported archive format")

def read_text_file(path: str):
    for encoding in ["utf-8", "utf-8-sig", "gb18030"]:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

@router.get("", response_model=List[schemas.Project])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@router.post("/create", response_model=schemas.Project)
def create_project(
    request: Request,
    name: str = Form(...),
    work_dir: str = Form("./"),
    output_dir: str = Form(None),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check if name exists
    if db.query(models.Project).filter(models.Project.name == name).first():
        raise HTTPException(status_code=400, detail="Project name already exists")

    # 2. Prepare path
    # Sanitize name
    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in ('-', '_')]).strip()
    project_path = os.path.join(PROJECTS_DIR, safe_name)
    
    if os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="Project directory already exists")

    os.makedirs(project_path)

    # 3. Save and Unzip
    ext = get_archive_extension(file.filename)
    if ext not in [".zip", ".7z", ".rar"]:
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        raise HTTPException(status_code=400, detail="Only .zip, .7z, .rar archives are supported")

    archive_path = os.path.join(project_path, f"upload{ext}")
    try:
        with open(archive_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        extract_archive(archive_path, ext, project_path)
        os.remove(archive_path)

    except Exception as e:
        if os.path.exists(project_path):
            shutil.rmtree(project_path) # Cleanup
        raise HTTPException(status_code=500, detail=f"Failed to process archive: {str(e)}")

    # 4. Create DB Record
    db_project = models.Project(
        name=name,
        path=project_path,
        work_dir=work_dir,
        output_dir=output_dir,
        description=description,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    create_audit_log(
        db=db,
        operation_type="CREATE",
        target_type="PROJECT",
        target_id=str(db_project.id),
        target_name=db_project.name,
        details=f"Created project '{db_project.name}'",
        operator_ip=request.client.host
    )

    return db_project

@router.get("/{project_id}/detect", response_model=dict)
def detect_project_framework(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    path = project.path
    if project.work_dir and project.work_dir != "./":
        path = os.path.join(path, project.work_dir)
        
    if not os.path.exists(path):
         return {"framework": "unknown", "command": ""}

    # 1. Check for Scrapy
    if os.path.exists(os.path.join(path, "scrapy.cfg")):
        # Try to find spider name
        spider_name = "myspider"
        # Simple heuristic: look for spiders folder
        # Usually: project_name/spiders
        # We can walk depth 2
        for root, dirs, files in os.walk(path):
            if "spiders" in dirs:
                spiders_dir = os.path.join(root, "spiders")
                for f in os.listdir(spiders_dir):
                    if f.endswith(".py") and f != "__init__.py":
                        # Try to read name
                        try:
                            with open(os.path.join(spiders_dir, f), 'r', encoding='utf-8') as pf:
                                content = pf.read()
                                import re
                                match = re.search(r"name\s*=\s*['\"](.+?)['\"]", content)
                                if match:
                                    spider_name = match.group(1)
                                    break
                        except:
                            pass
                break
                
        return {
            "framework": "scrapy", 
            "command": f"scrapy crawl {spider_name}",
            "description": "Detected Scrapy project"
        }

    # 2. Advanced Detection: Check requirements.txt or imports for other frameworks
    detected_framework = None
    
    # Helper to check content
    def check_file_content(filepath, keywords):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                for k in keywords:
                    if k.lower() in content:
                        return k
        except:
            pass
        return None

    # Check requirements.txt
    req_path = os.path.join(path, "requirements.txt")
    if os.path.exists(req_path):
        fw = check_file_content(req_path, ["playwright", "selenium", "DrissionPage"])
        if fw:
            detected_framework = fw

    # If not found in requirements, scan python files (shallow scan)
    if not detected_framework:
        for root, dirs, files in os.walk(path):
            if root != path: continue # Only scan root for efficiency
            for f in files:
                if f.endswith(".py"):
                    fw = check_file_content(os.path.join(root, f), ["playwright", "selenium", "DrissionPage"])
                    if fw:
                        detected_framework = fw
                        break
            if detected_framework: break

    # Determine command based on file existence
    command = "python main.py"
    desc_suffix = ""
    
    if os.path.exists(os.path.join(path, "main.py")):
        command = "python main.py"
        desc_suffix = " (main.py)"
    elif os.path.exists(os.path.join(path, "app.py")):
        command = "python app.py"
        desc_suffix = " (app.py)"
    else:
        command = "python script.py"
        desc_suffix = " (Generic)"

    if detected_framework:
        # Normalize name
        fw_name = detected_framework
        if fw_name.lower() == "drissionpage": fw_name = "DrissionPage"
        elif fw_name.lower() == "playwright": fw_name = "Playwright"
        elif fw_name.lower() == "selenium": fw_name = "Selenium"
        
        return {
            "framework": fw_name.lower(),
            "command": command,
            "description": f"Detected {fw_name} project{desc_suffix}"
        }

    # 3. Fallback: Generic Python
    if os.path.exists(os.path.join(path, "main.py")):
        return {
            "framework": "python",
            "command": "python main.py",
            "description": "Detected main.py"
        }
        
    if os.path.exists(os.path.join(path, "app.py")):
        return {
            "framework": "python",
            "command": "python app.py",
            "description": "Detected app.py"
        }

    # 4. Check for requirements.txt but no main script
    if os.path.exists(os.path.join(path, "requirements.txt")):
         return {
            "framework": "python",
            "command": "python script.py",
            "description": "Detected requirements.txt"
        }

    return {"framework": "unknown", "command": ""}

@router.put("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    project_in: schemas.ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_in.name is not None:
        # Check if name exists (excluding self)
        existing = db.query(models.Project).filter(models.Project.name == project_in.name).filter(models.Project.id != project_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Project name already exists")
        project.name = project_in.name

    if project_in.work_dir is not None:
        project.work_dir = project_in.work_dir
        
    if project_in.output_dir is not None:
        project.output_dir = project_in.output_dir
        
    if project_in.description is not None:
        project.description = project_in.description

    project.updated_at = datetime.datetime.now()
    db.commit()
    db.refresh(project)
    
    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="PROJECT",
        target_id=str(project.id),
        target_name=project.name,
        details=f"Updated project '{project.name}'",
        operator_ip=request.client.host
    )
    
    return project

# Helper to remove read-only files (fixes Windows deletion issues)
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

@router.delete("/{project_id}")
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if used by any task
    related_tasks = db.query(Task).filter(Task.project_id == project_id).all()
    if related_tasks:
        task_names = ", ".join([t.name for t in related_tasks])
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete project: It is currently used by tasks: {task_names}"
        )

    # Audit Log
    create_audit_log(
        db=db,
        operation_type="DELETE",
        target_type="PROJECT",
        target_id=str(project.id),
        target_name=project.name,
        details=f"Deleted project '{project.name}'",
        operator_ip=request.client.host
    )

    # Remove directory with robust logic
    if os.path.exists(project.path):
        print(f"Deleting project directory: {project.path}")
        
        # 1. Rename to trash (Windows trick to unlock name immediately)
        target_dir = project.path
        try:
            timestamp = int(time.time())
            trash_dir = f"{project.path}_trash_{timestamp}"
            os.rename(project.path, trash_dir)
            target_dir = trash_dir
        except Exception as e:
            print(f"Rename failed: {e}")
            
        # 2. Robust cleanup loop
        max_retries = 5
        for i in range(max_retries):
            if not os.path.exists(target_dir):
                break
            
            try:
                shutil.rmtree(target_dir, onerror=remove_readonly)
            except Exception as e:
                print(f"shutil.rmtree failed: {e}")
                
            if not os.path.exists(target_dir):
                break
                
            # Windows force delete
            if platform.system() == "Windows":
                try:
                    subprocess.run(f'icacls "{target_dir}" /grant Everyone:F /T /C /Q', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(f'del /f /s /q /a "{target_dir}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(f'rmdir /s /q "{target_dir}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except:
                    pass
            
            time.sleep(1)
            
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}

def build_file_tree(base_path, rel_path=""):
    items = []
    # Ensure base_path doesn't end with slash to avoid double slash issues, though join handles it
    full_path = os.path.join(base_path, rel_path)
    
    if not os.path.exists(full_path):
        return []

    try:
        for entry in os.scandir(full_path):
            if entry.name == '__pycache__' or entry.name.startswith('.'):
                continue
                
            entry_rel_path = os.path.join(rel_path, entry.name).replace("\\", "/")
            item = {
                "label": entry.name,
                "path": entry_rel_path,
                "type": "dir" if entry.is_dir() else "file",
            }
            if entry.is_dir():
                item["children"] = build_file_tree(base_path, entry_rel_path)
            items.append(item)
    except PermissionError:
        pass # Skip unreadable directories
    
    # Sort: directories first, then files
    items.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["label"].lower()))
    return items

@router.get("/{project_id}/files")
def get_project_files(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not os.path.exists(project.path):
        return []
        
    return build_file_tree(project.path)

@router.get("/{project_id}/files/content")
def get_file_content(project_id: int, path: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Security check: Ensure path is within project.path
    full_path = os.path.abspath(os.path.join(project.path, path))
    if not full_path.startswith(os.path.abspath(project.path)):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt")
        
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        content = read_text_file(full_path)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.post("/{project_id}/files/save")
async def save_file_content(
    project_id: int, 
    body: schemas.FileSaveRequest,
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Security check
    full_path = os.path.abspath(os.path.join(project.path, body.path))
    if not full_path.startswith(os.path.abspath(project.path)):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt")
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(body.content)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

# Add endpoint to browse server directories (for output_dir selection)
class DirListRequest(BaseModel):
    path: str = "/"

# Define allowed base directories for browsing
ALLOWED_BROWSE_DIRS = [
    PROJECTS_DIR,  # Project uploads directory
    os.path.abspath(os.path.join(os.getcwd(), "..", "Data")),  # Data directory (uppercase)
    os.path.abspath("/data"),  # Data directory (lowercase, docker volume mount)
    os.path.abspath(os.path.join(os.getcwd(), "envs")),  # Environments directory
    os.path.abspath(os.path.join(os.getcwd(), "logs")),  # Logs directory
]

def is_path_allowed(target_path: str) -> bool:
    """Check if the target path is within allowed directories."""
    abs_target = os.path.abspath(target_path)
    for allowed_dir in ALLOWED_BROWSE_DIRS:
        abs_allowed = os.path.abspath(allowed_dir)
        if abs_target.startswith(abs_allowed + os.sep) or abs_target == abs_allowed:
            return True
    return False

@router.post("/browse-dirs")
def browse_server_directories(request: DirListRequest):
    # Only allow browsing, no modification
    target_path = request.path

    # Validate path is not empty
    if not target_path or target_path == "":
        # Default to projects directory
        target_path = PROJECTS_DIR

    # Security check: ensure path is within allowed directories
    if not is_path_allowed(target_path):
        raise HTTPException(status_code=403, detail="Access denied: Path is not in allowed directories")

    # Additional check: resolve any path traversal attempts
    abs_target = os.path.abspath(target_path)
    if not is_path_allowed(abs_target):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt detected")

    if not os.path.exists(abs_target):
        raise HTTPException(status_code=404, detail="Path not found")

    # Don't allow going above allowed directories
    for allowed_dir in ALLOWED_BROWSE_DIRS:
        abs_allowed = os.path.abspath(allowed_dir)
        parent = abs_target
        while parent:
            parent = os.path.dirname(parent)
            if parent == abs_allowed:
                break
            if not parent or parent == os.path.dirname(parent):  # Reached root
                # Check if we're still in an allowed path
                if not is_path_allowed(abs_target):
                    raise HTTPException(status_code=403, detail="Access denied: Cannot browse outside allowed directories")
                break

    items = []
    try:
        for entry in os.scandir(abs_target):
            if entry.is_dir():
                try:
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": "dir"
                    })
                except:
                    pass
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")

    items.sort(key=lambda x: x["name"].lower())

    # Add parent dir only if it's within allowed directories
    parent = os.path.dirname(abs_target)
    if parent and is_path_allowed(parent):
         items.insert(0, {"name": "..", "path": parent, "type": "dir"})

    return {
        "current_path": abs_target,
        "items": items
    }
