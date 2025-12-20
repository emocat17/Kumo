from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PythonVersion(Base):
    __tablename__ = "python_versions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="")
    version = Column(String, index=True)
    path = Column(String)
    is_default = Column(Boolean, default=False)
    status = Column(String, default="ready")
    is_conda = Column(Boolean, default=False) # Flag to track if it was created by Conda
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
