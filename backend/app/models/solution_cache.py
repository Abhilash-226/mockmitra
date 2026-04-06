from beanie import Document, Indexed
from datetime import datetime, timezone
from pydantic import Field
from typing import Optional, Annotated


class SolutionCache(Document):
    """Stores generated solutions keyed by canonicalized question payload."""

    cache_key: Annotated[str, Indexed(unique=True)]
    solution_text: str
    provider: str = "gemini"
    model_name: Optional[str] = None
    question_id: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "solution_cache"
        indexes = [
            [("cache_key", 1)],
            [("question_id", 1)],
            [("updated_at", -1)],
        ]
