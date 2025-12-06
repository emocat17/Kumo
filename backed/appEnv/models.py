from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PythonVersion(Base):
    __tablename__ = "python_versions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    version = Column(String, unique=True, index=True)
    path = Column(String)
    is_default = Column(Boolean, default=False)
    status = Column(String, default="ready")
    is_conda = Column(Boolean, default=False) # Flag to track if it was created by Conda
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PythonEnv(Base):
    __tablename__ = "python_envs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    path = Column(String, unique=True)
    description = Column(String, default="")
    status = Column(String, default="installing") # installing, ready, error
    packages = Column(String, default="") # Store requested packages
    python_version_id = Column(Integer, ForeignKey("python_versions.id"))
    
    python_version = relationship("PythonVersion")
