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
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Exam Settings
    EXAM_CONFIGS_PATH: str = "exam_configs"
    
    class Config:
        import os
        from pathlib import Path
        env_file = str(Path(__file__).parent.parent.parent / ".env")


settings = Settings()

# Export GCP credentials to environment for Google SDKs
if settings.GOOGLE_APPLICATION_CREDENTIALS:
    import os
    from pathlib import Path
    
    # If it's a relative path, make it absolute relative to the backend directory
    cred_path = Path(settings.GOOGLE_APPLICATION_CREDENTIALS)
    if not cred_path.is_absolute():
        backend_dir = Path(__file__).parent.parent.parent
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(backend_dir / cred_path)
    else:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)
