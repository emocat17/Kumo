
from sqlalchemy import Column, Integer, String, DateTime, Text
from core.database import Base
import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    operation_type = Column(String, index=True)  # CREATE, UPDATE, DELETE, EXECUTE, BACKUP, etc.
    target_type = Column(String, index=True)     # PROJECT, ENVIRONMENT, TASK, SYSTEM
    target_id = Column(String, nullable=True)    # ID of the target
    target_name = Column(String, nullable=True)  # Name snapshot
    details = Column(Text, nullable=True)        # JSON details or description
    status = Column(String, default="SUCCESS")   # SUCCESS, FAILURE
    operator_ip = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
