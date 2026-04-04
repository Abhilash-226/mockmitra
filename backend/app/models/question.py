from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime, timezone
from typing import Optional, Dict, Annotated, Any
from enum import Enum


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionSource(str, Enum):
    PYQ = "pyq"  # Previous Year Question
    AI_GENERATED = "ai_generated"
    MANUAL = "manual"


class Question(Document):
    # Question content
    question_text: str
    options: Dict[str, Any]  # {"a": "...", "b": "...", "c": "...", "d": "..."}
    correct_option: str  # a, b, c, or d
    image: Optional[str] = None
    explanation: Optional[str] = None
    
    # Categorization
    exam_code: Annotated[str, Indexed()]  # ssc_cgl, jee_main, etc.
    section: Annotated[Optional[str], Indexed()] = None  # Quantitative Aptitude, Reasoning, etc.
    topic: Annotated[Optional[str], Indexed()] = None  # Algebra, Number System, etc.
    subtopic: Optional[str] = None
    
    # Metadata
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    source: QuestionSource = QuestionSource.MANUAL
    year: Optional[int] = None  # For PYQs
    
    # Statistics
    times_attempted: int = 0
    times_correct: int = 0
    avg_time_seconds: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "questions"
        indexes = [
            [("exam_code", 1), ("section", 1)],
            [("exam_code", 1), ("topic", 1)],
            [("exam_code", 1), ("section", 1), ("topic", 1), ("difficulty", 1)],  # unseen-query index
            [("exam_code", 1), ("section", 1), ("source", 1)],                   # pool-source filter
        ]
