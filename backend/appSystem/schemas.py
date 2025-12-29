from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SystemConfigBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

class SystemConfigCreate(SystemConfigBase):
    pass

class SystemConfigUpdate(SystemConfigBase):
    pass

class SystemConfig(SystemConfigBase):
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Environment Variables ---

class EnvVarBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    is_secret: bool = False

class EnvVarCreate(EnvVarBase):
    pass

class EnvVarUpdate(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None

class EnvVarResponse(BaseModel):
    id: int
    key: str
    value: str # Masked if secret
    description: Optional[str] = None
    is_secret: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
