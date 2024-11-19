from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Keyword Analysis API"
    DATABASE_URL: str
    
    class Config:
        env_file = ".env"

settings = Settings() 