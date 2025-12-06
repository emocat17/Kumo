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
        work_dir=work_dir
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
