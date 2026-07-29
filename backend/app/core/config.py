from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "MockMitra"
    DEBUG: bool = True
    
    # Database (MongoDB Atlas)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "mockmitra"
    
    # JWT Settings
    JWT_SECRET: str = "change-this-in-production"
    SECRET_KEY: Optional[str] = None
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
    GEMINI_GENERATION_MODEL: str = "gemini-2.5-flash"
    GEMINI_VALIDATOR_MODEL: str = "gemini-2.5-flash"
    GEMINI_VALIDATOR_THINKING_BUDGET: int = 1024

    # Generation/Validation Throughput Controls
    AI_GENERATION_SECTION_MAX_WORKERS: int = 3
    AI_GENERATION_SECTION_TIMEOUT_SECONDS: int = 180
    AI_GENERATION_OVERALL_TIMEOUT_SECONDS: int = 0
    AI_GENERATION_TIMEOUT_PER_QUESTION_SECONDS: int = 75
    VALIDATOR_GLOBAL_CONCURRENCY: int = 2
    VALIDATOR_MAX_CALLS_PER_SECOND: float = 0.7
    VALIDATOR_429_COOLDOWN_SECONDS: int = 25
    VALIDATOR_NUMERIC_EQUIVALENCE_TOLERANCE: float = 1e-6
    GENERATOR_GLOBAL_CONCURRENCY: int = 1
    GENERATOR_MAX_CALLS_PER_SECOND: float = 0.5
    GENERATOR_429_COOLDOWN_SECONDS: int = 12
    
    # Exam Settings
    EXAM_CONFIGS_PATH: str = "exam_configs"
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "https://mockmitra.app",
        "https://www.mockmitra.app",
        "https://studysphere-frontend-gtvp.onrender.com",
    ]
    # Allow all origins in dev (set to true when using port forwarding / tunnels)
    CORS_ALLOW_ALL: bool = False
    
    class Config:
        import os
        from pathlib import Path
        env_file = str(Path(__file__).parent.parent.parent / ".env")

    @property
    def jwt_signing_key(self) -> str:
        """Compatibility bridge for older SECRET_KEY deployments."""
        return self.SECRET_KEY or self.JWT_SECRET


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
