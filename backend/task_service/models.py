from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    status = Column(String, default="paused", index=True)  # 添加索引 - 经常按状态查询
    command = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)  # 添加索引
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
    priority = Column(Integer, default=0, index=True) # 0=Normal, 1=High, 2=Critical - 添加索引

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")

class TaskExecution(Base):
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), index=True)  # 添加索引
    status = Column(String, index=True)  # 添加索引 - 经常按状态查询
    attempt = Column(Integer, default=1)
    start_time = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # 添加索引
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Float, nullable=True)
    log_file = Column(String, nullable=True)
    output = Column(Text, nullable=True) # Snippet of output
    max_cpu_percent = Column(Float, nullable=True)
    max_memory_mb = Column(Float, nullable=True)
    
    task = relationship("Task", back_populates="executions")
