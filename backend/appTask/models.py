from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    status = Column(String, default="paused") # active, paused, error
    command = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    env_id = Column(Integer, ForeignKey("python_versions.id"), nullable=True)
    node_id = Column(String, nullable=True) # For distributed nodes
    description = Column(String, default="")
    
    # Trigger config
    trigger_type = Column(String) # interval, date, cron, immediate
    trigger_value = Column(String) # JSON string storing details
    
    # Reliability config
    retry_count = Column(Integer, default=0)
    retry_delay = Column(Integer, default=60) # seconds
    timeout = Column(Integer, default=3600) # seconds

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")

class TaskExecution(Base):
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    status = Column(String) # success, failed, running, timeout, stopped
    attempt = Column(Integer, default=1)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)
    log_file = Column(String, nullable=True)
    output = Column(Text, nullable=True) # Snippet of output
    
    task = relationship("Task", back_populates="executions")
