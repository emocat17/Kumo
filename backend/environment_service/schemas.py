from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class PythonVersionBase(BaseModel):
    name: Optional[str] = None
    version: str
    path: str
    status: str = "ready"
    is_default: bool = False
    is_conda: bool = False
    is_in_use: bool = False # Whether this version is used by any task

class PythonVersionCreate(PythonVersionBase):
    pass

class PythonVersion(PythonVersionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
