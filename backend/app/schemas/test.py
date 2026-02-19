from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.test import TestType, TestStatus


class TestCreate(BaseModel):
    title: str
    exam_code: str
    test_type: TestType = TestType.FULL_LENGTH
    section: Optional[str] = None  # Backward compatibility
    sections: Optional[List[str]] = None  # Selected section codes
    topics: Optional[List[str]] = None  # Selected topic codes
    difficulty: Optional[str] = "mixed"  # easy, medium, hard, mixed
    custom_question_count: Optional[int] = None
    custom_duration_minutes: Optional[int] = None


class TestResponse(BaseModel):
    id: Any = Field(alias="_id")
    title: str
    exam_code: str
    test_type: TestType
    total_questions: int
    total_marks: float
    duration_minutes: int
    negative_marking: float
    sections: Optional[List[Dict[str, Any]]]
    created_at: datetime
    
    @field_serializer('id')
    def serialize_id(self, value):
        return str(value) if value else None
        
    @field_serializer('created_at')
    def serialize_dt(self, value):
        if value:
            if value.tzinfo is None:
                return value.isoformat() + "Z"
            return value.isoformat().replace("+00:00", "Z")
        return None
    
    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v.tzinfo is None else v.isoformat()
        }


class TestAttemptCreate(BaseModel):
    test_id: str


class TestAttemptResponse(BaseModel):
    id: Any = Field(alias="_id")
    test_id: Any
    test_title: Optional[str] = None
    exam_code: Optional[str] = None
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    sections: Optional[List[Dict[str, Any]]] = None
    status: TestStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    time_taken_seconds: Optional[int]
    total_attempted: int
    correct_answers: int
    wrong_answers: int
    skipped: int
    score: float
    percentage: float
    section_results: Optional[Dict[str, Any]]
    
    @field_serializer('id', 'test_id')
    def serialize_ids(self, value):
        return str(value) if value else None
        
    @field_serializer('started_at', 'completed_at')
    def serialize_dts(self, value):
        if value:
            # Ensure Z suffix for UTC synchronization with browser
            if value.tzinfo is None:
                return value.isoformat() + "Z"
            return value.isoformat().replace("+00:00", "Z")
        return None
    
    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v.tzinfo is None else v.isoformat()
        }


class SubmitAnswerRequest(BaseModel):
    question_id: str
    selected_option: Optional[str] = None  # a, b, c, d or None for skip
    is_marked_for_review: bool = False
    time_spent_seconds: int = 0


class SubmitTestRequest(BaseModel):
    responses: List[SubmitAnswerRequest]
