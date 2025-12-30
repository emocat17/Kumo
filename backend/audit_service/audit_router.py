
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from core.database import get_db
from . import models, schemas
from typing import List, Optional

router = APIRouter()

@router.get("", response_model=schemas.AuditLogList)
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    target_type: Optional[str] = None,
    operation_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.AuditLog)
    
    if target_type:
        query = query.filter(models.AuditLog.target_type == target_type)
    if operation_type:
        query = query.filter(models.AuditLog.operation_type == operation_type)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(
            models.AuditLog.target_name.ilike(search_term),
            models.AuditLog.details.ilike(search_term),
            models.AuditLog.operator_ip.ilike(search_term)
        ))
        
    total = query.count()
    items = query.order_by(models.AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"total": total, "items": items}

@router.get("/types")
async def get_audit_types(db: Session = Depends(get_db)):
    """Return available operation types and target types for filtering"""
    ops = db.query(models.AuditLog.operation_type).distinct().all()
    targets = db.query(models.AuditLog.target_type).distinct().all()
    
    return {
        "operation_types": [o[0] for o in ops if o[0]],
        "target_types": [t[0] for t in targets if t[0]]
    }
