from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional, Annotated
from pymongo import IndexModel


class PyQSolution(Document):
    """Stored, pre-generated solution for a PYQ question."""

    paper_id: Annotated[str, Indexed()]
    question_number: Annotated[int, Indexed()]

    question_text: str
    correct_answer: Optional[str] = None
    solution_text: str
    source_hash: Annotated[str, Indexed()]

    provider: str = "gemini"
    model_name: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "pyq_solutions"
        indexes = [
            IndexModel([("paper_id", 1), ("question_number", 1)], unique=True),
            [("paper_id", 1)],
            [("source_hash", 1)],
            [("updated_at", -1)],
        ]
