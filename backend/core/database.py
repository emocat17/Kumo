"""
数据库连接管理模块
统一管理数据库连接、会话和连接池配置
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# 使用配置中的数据库 URL
SQLALCHEMY_DATABASE_URL = settings.database_url

# 配置连接池
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=settings.database_pool_pre_ping,  # 连接健康检查
    echo=False  # 设置为 True 可以查看 SQL 语句
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    数据库会话依赖注入
    用于 FastAPI 路由中获取数据库会话
    
    Yields:
        Session: 数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    创建所有表结构
    """
    import os
    # 确保数据目录存在（已在 settings.ensure_directories() 中处理）
    logger.info(f"Initializing database at {SQLALCHEMY_DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
