from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.question import DifficultyLevel, QuestionSource


class QuestionCreate(BaseModel):
    question_text: str
    options: Dict[str, str]  # {"a": "...", "b": "...", "c": "...", "d": "..."}
    correct_option: str
    explanation: Optional[str] = None
    exam_code: str
    section: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    source: QuestionSource = QuestionSource.MANUAL
    year: Optional[int] = None


class QuestionResponse(BaseModel):
    id: Any = Field(alias="_id")
    question_text: str
    options: Dict[str, str]
    correct_option: str
    explanation: Optional[str]
    exam_code: str
    section: Optional[str]
    topic: Optional[str]
    difficulty: DifficultyLevel
    source: QuestionSource
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class QuestionInTest(BaseModel):
    """Question as shown during test (without correct answer)"""
    id: Any = Field(alias="_id")
    question_text: str
    options: Dict[str, str]
    section: Optional[str]
    
    class Config:
        from_attributes = True
        populate_by_name = True
