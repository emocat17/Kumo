
from sqlalchemy.orm import Session
from .models import AuditLog
from typing import Optional

def create_audit_log(
    db: Session,
    operation_type: str,
    target_type: str,
    target_id: Optional[str] = None,
    target_name: Optional[str] = None,
    details: Optional[str] = None,
    status: str = "SUCCESS",
    operator_ip: Optional[str] = None
):
    """
    Helper function to create an audit log entry.
    """
    db_log = AuditLog(
        operation_type=operation_type,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        target_name=target_name,
        details=details,
        status=status,
        operator_ip=operator_ip
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
