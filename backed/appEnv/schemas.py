from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PythonVersionBase(BaseModel):
    name: Optional[str] = None
    version: str
    path: str
    status: str = "ready"
    is_default: bool = False
    is_conda: bool = False 

class PythonVersionCreate(PythonVersionBase):
    pass

class PythonVersion(PythonVersionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
