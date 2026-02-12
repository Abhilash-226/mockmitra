from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any, Union


class TopicConfig(BaseModel):
    """Topic configuration with metadata"""
    name: str
    code: str
    question_count: Optional[int] = None
    
    @classmethod
    def from_string(cls, topic_name: str) -> "TopicConfig":
        """Create TopicConfig from a string topic name"""
        return cls(
            name=topic_name,
            code=topic_name.lower().replace(" ", "_").replace("-", "_"),
            question_count=None
        )


class SectionConfig(BaseModel):
    name: str
    code: str
    total_questions: int
    marks_per_question: float
    negative_marks: float
    time_limit_minutes: Optional[int] = None  # If section has separate timer
    topics: List[TopicConfig]
    topic_bank: List[TopicConfig] = []
    
    @field_validator('topics', 'topic_bank', mode='before')
    @classmethod
    def convert_topics(cls, v):
        """Convert string topics to TopicConfig objects for backward compatibility"""
        if not v:
            return []
        
        result = []
        for topic in v:
            if isinstance(topic, str):
                result.append(TopicConfig.from_string(topic))
            elif isinstance(topic, dict):
                result.append(TopicConfig(**topic))
            else:
                result.append(topic)
        return result


class ExamConfig(BaseModel):
    """Exam configuration schema - loaded from YAML/JSON files"""
    exam_code: str
    exam_name: str
    description: str
    
    # Timing
    total_duration_minutes: int
    section_wise_timing: bool = False
    
    # Marking scheme
    default_marks_per_question: float = 1.0
    default_negative_marks: float = 0.0
    
    # Sections
    sections: List[SectionConfig]
    
    # Instructions
    instructions: List[str]
    
    # Metadata
    conducting_body: str
    frequency: str  # yearly, twice_yearly, etc.
    official_website: Optional[str] = None
    
    @property
    def total_questions(self) -> int:
        return sum(s.total_questions for s in self.sections)
    
    @property
    def total_marks(self) -> float:
        return sum(s.total_questions * s.marks_per_question for s in self.sections)


class ExamListResponse(BaseModel):
    exam_code: str
    exam_name: str
    description: str
    total_questions: int
    duration_minutes: int
    sections: List[str]
