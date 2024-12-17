from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Keyword Analysis API"
    API_V1_STR: str = "/api/v1"
    
    # JWT相关配置
    SECRET_KEY: str = "your-secret-key-here"  # 在生产环境中应该使用环境变量
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # token 过期时间为30分钟
    
    # 数据库配置
    DATABASE_URL: str
    
    # OpenAI配置 - 直接指定用于调试
    OPENAI_API_KEY: str = "sk-1tXBPFQM7vT44xis1La6CzL8tJvA9NEKG8oJDGmtac17OhWa"  # 替换为你的 API key
    OPENAI_BASE_URL: str = "https://yunwu.ai/v1"  # 替换为你的 base URL
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:7243",
        "http://127.0.0.1:7243",
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "file://",
        "*"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("\n" + "="*50)
        print("OpenAI Configuration:")
        print(f"API Key: {self.OPENAI_API_KEY}")
        print(f"Base URL: {self.OPENAI_BASE_URL}")
        print("="*50 + "\n")

settings = Settings() 