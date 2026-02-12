from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional, Annotated, Literal


class User(Document):
    email: Annotated[str, Indexed(unique=True)]
    hashed_password: Optional[str] = None  # Optional for OAuth users
    full_name: Optional[str] = None
    
    # OAuth provider info
    auth_provider: Literal["local", "google"] = "local"
    google_id: Optional[str] = None
    profile_picture: Optional[str] = None
    
    # Target exam preferences
    target_exam: Optional[str] = None
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "target_exam": "ssc_cgl",
                "auth_provider": "local"
            }
        }
