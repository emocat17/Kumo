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
        orm_mode = True

class PythonEnvBase(BaseModel):
    name: str
    path: str
    description: Optional[str] = ""
    status: str = "installing"
    packages: Optional[str] = ""
    python_version_id: int

class PythonEnvCreate(BaseModel):
    name: str
    python_version_id: int
    description: Optional[str] = ""
    packages: Optional[str] = "" 
    install_method: str = "pip" 

class PythonEnv(PythonEnvBase):
    id: int
    python_version: Optional[PythonVersion] = None

    class Config:
        orm_mode = True
