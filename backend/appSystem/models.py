from sqlalchemy import Column, String, DateTime, Integer, Boolean
from sqlalchemy.sql import func
from app.database import Base

class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EnvironmentVariable(Base):
    __tablename__ = "environment_variables"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False) # Stores encrypted text if is_secret=True
    description = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
