import os
import shutil
import zipfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from appProject import models, schemas
import datetime

router = APIRouter()

PROJECTS_DIR = os.path.abspath(os.path.join(os.getcwd(), "projects"))

if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

@router.get("/", response_model=List[schemas.Project])
async def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).all()

@router.post("/create", response_model=schemas.Project)
async def create_project(
    name: str = Form(...),
    work_dir: str = Form("./"),
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
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.delete("/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Remove directory
    if os.path.exists(project.path):
        try:
            shutil.rmtree(project.path)
        except Exception as e:
            print(f"Error removing directory: {e}")
            # Continue to remove DB record even if file removal fails (or maybe not?)
            # Let's proceed
            
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
