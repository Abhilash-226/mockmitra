from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "MockMitra"
    DEBUG: bool = True
    
    # Database (MongoDB Atlas)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "mockmitra"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    
    # AI Settings
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # Exam Settings
    EXAM_CONFIGS_PATH: str = "exam_configs"
    
    class Config:
        env_file = ".env"


settings = Settings()
