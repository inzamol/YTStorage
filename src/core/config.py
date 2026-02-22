from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    DATABASE_URL: str = "sqlite:///./ytmanager.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # YouTube API Scopes
    YOUTUBE_SCOPES: list[str] = ["https://www.googleapis.com/auth/youtube"]
    
    # FastAPI
    PROJECT_NAME: str = "YTStorage Manager"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
