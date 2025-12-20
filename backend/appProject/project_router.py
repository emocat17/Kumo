import os
import shutil
import zipfile
import platform
import subprocess
import time
import stat
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from appProject import models, schemas
from appTask.models import Task
import datetime
from pydantic import BaseModel

router = APIRouter()

PROJECTS_DIR = os.path.abspath(os.path.join(os.getcwd(), "projects"))

if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

# Helper to run DB migration for output_dir
def ensure_project_columns():
    db_path = "backend/data/TaskManage.db" # Hardcoded relative path, should be config based
    # Better to rely on SQLALCHEMY_DATABASE_URL but that's in app.database
    # Let's import it
    from app.database import SQLALCHEMY_DATABASE_URL
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

@router.get("", response_model=List[schemas.Project])
async def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@router.post("/create", response_model=schemas.Project)
async def create_project(
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
    zip_path = os.path.join(project_path, "upload.zip")
    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        if not zipfile.is_zipfile(zip_path):
             raise Exception("Uploaded file is not a valid zip file")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_path)
        
        os.remove(zip_path)

    except Exception as e:
        if os.path.exists(project_path):
            shutil.rmtree(project_path) # Cleanup
        raise HTTPException(status_code=500, detail=f"Failed to process zip: {str(e)}")

    # 4. Create DB Record
    db_project = models.Project(
        name=name,
        path=project_path,
        work_dir=work_dir,
        description=description,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.put("/{project_id}", response_model=schemas.Project)
async def update_project(
    project_id: int,
    project_in: schemas.ProjectUpdate,
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
    return project

# Helper to remove read-only files (fixes Windows deletion issues)
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
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
async def get_project_files(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not os.path.exists(project.path):
        return []
        
    return build_file_tree(project.path)

@router.get("/{project_id}/files/content")
async def get_file_content(project_id: int, path: str, db: Session = Depends(get_db)):
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
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except UnicodeDecodeError:
         raise HTTPException(status_code=400, detail="Binary or non-UTF-8 file cannot be opened")
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

@router.post("/browse-dirs")
async def browse_server_directories(request: DirListRequest):
    # Only allow browsing, no modification
    target_path = request.path
    if not target_path or target_path == "":
        if platform.system() == "Windows":
             target_path = "C:\\" # Or maybe just list drives? But let's start simple
        else:
             target_path = "/"
             
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Path not found")
        
    items = []
    try:
        for entry in os.scandir(target_path):
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
    
    # Add parent dir
    parent = os.path.dirname(target_path)
    if parent and parent != target_path:
         items.insert(0, {"name": "..", "path": parent, "type": "dir"})
         
    return {
        "current_path": os.path.abspath(target_path),
        "items": items
    }
