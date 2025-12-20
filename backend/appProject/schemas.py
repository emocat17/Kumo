from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProjectBase(BaseModel):
    name: str
    work_dir: str = "./"
    description: Optional[str] = None
    output_dir: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    work_dir: Optional[str] = None
    description: Optional[str] = None
    output_dir: Optional[str] = None

class Project(ProjectBase):
    id: int
    path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FileSaveRequest(BaseModel):
    path: str
    content: str
