
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AuditLogBase(BaseModel):
    operation_type: str
    target_type: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    details: Optional[str] = None
    status: str = "SUCCESS"
    operator_ip: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogOut(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class AuditLogList(BaseModel):
    total: int
    items: List[AuditLogOut]
