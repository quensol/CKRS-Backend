from typing import Generator
from app.core.database import SessionLocal

def get_db() -> Generator:
    """
    数据库会话依赖项，用于FastAPI的依赖注入系统
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()