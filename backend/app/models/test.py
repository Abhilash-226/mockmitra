from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated
from enum import Enum


class TestType(str, Enum):
    FULL_LENGTH = "full_length"
    SECTIONAL = "sectional"
    TOPIC_WISE = "topic_wise"
    CUSTOM = "custom"


class TestStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Test(Document):
    """Template for a test (can be reused)"""
    
    # Test info
    title: str
    exam_code: Annotated[str, Indexed()]
    test_type: TestType = TestType.FULL_LENGTH
    
    # Configuration
    total_questions: int
    total_marks: float
    duration_minutes: int
    negative_marking: float = 0.0  # e.g., 0.25 for 1/4th negative
    
    # Section-wise config
    sections: Optional[List[Dict[str, Any]]] = None  # [{"name": "QA", "questions": 25, "marks": 50}, ...]
    
    # Question IDs (stored as list of ObjectId references)
    question_ids: List[PydanticObjectId] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "tests"


class TestResponse(Document):
    """Individual question responses in a test attempt"""
    
    # References
    attempt_id: Annotated[PydanticObjectId, Indexed()]
    question_id: PydanticObjectId
    
    # Response
    selected_option: Optional[str] = None  # a, b, c, d, or null if skipped
    is_correct: Optional[bool] = None
    is_marked_for_review: bool = False
    time_spent_seconds: int = 0
    
    # Timestamps
    answered_at: Optional[datetime] = None
    
    class Settings:
        name = "test_responses"


class TestAttempt(Document):
    """User's attempt at a test"""
    
    # References
    user_id: Annotated[PydanticObjectId, Indexed()]
    test_id: Annotated[PydanticObjectId, Indexed()]
    
    # Status
    status: TestStatus = TestStatus.NOT_STARTED
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_taken_seconds: Optional[int] = None
    
    # Results
    total_attempted: int = 0
    correct_answers: int = 0
    wrong_answers: int = 0
    skipped: int = 0
    score: float = 0.0
    percentage: float = 0.0
    
    # Section-wise results
    section_results: Optional[Dict[str, Any]] = None
    
    class Settings:
        name = "test_attempts"
        indexes = [
            [("user_id", 1), ("status", 1)],
            [("user_id", 1), ("test_id", 1)],
        ]
