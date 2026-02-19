from pydantic import BaseModel, field_validator, computed_field, model_validator
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
    """Section configuration (e.g., Algebra, Mechanics)"""
    name: str
    code: str
    total_questions: int
    marks_per_question: float
    negative_marks: float
    time_limit_minutes: Optional[int] = None
    topics: List[TopicConfig] = []
    
    @field_validator('topics', mode='before')
    @classmethod
    def convert_topics(cls, v):
        if not v: return []
        result = []
        for topic in v:
            if isinstance(topic, str):
                result.append(TopicConfig.from_string(topic))
            elif isinstance(topic, dict):
                result.append(TopicConfig(**topic))
            else:
                result.append(topic)
        return result


class SubjectConfig(BaseModel):
    """Subject configuration (e.g., Mathematics, Physics)"""
    name: str
    code: str
    sections: List[SectionConfig]
    
    @property
    def total_questions(self) -> int:
        return sum(s.total_questions for s in self.sections)


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
    
    # Subjects (Mathematics, Physics, Chemistry)
    subjects: Optional[List[SubjectConfig]] = None
    
    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_sections(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If subjects is already present, we're good
            if 'subjects' in data and data['subjects']:
                return data
                
            # If missing subjects but has sections (legacy format)
            if 'sections' in data and data['sections']:
                legacy_sections = data['sections']
                new_subjects = []
                
                for section_data in legacy_sections:
                    # Map OLD section to NEW subject + NEW single section
                    # This preserves the 3-level hierarchy for the UI
                    section_name = section_data.get('name', 'General')
                    section_code = section_data.get('code', 'general')
                    
                    new_subjects.append({
                        'name': section_name,
                        'code': section_code,
                        'sections': [section_data] # The subject has one section which is itself
                    })
                
                data['subjects'] = new_subjects
                # We don't delete 'sections' as it might be used by @computed_field later
                # but Pydantic will ignore extra fields not in model unless configured otherwise
                
        return data
    
    @computed_field
    @property
    def sections(self) -> List[SectionConfig]:
        """Flat list of all sections across all subjects for backward compatibility"""
        all_sections = []
        for sub in self.subjects:
            all_sections.extend(sub.sections)
        return all_sections
    
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
    subjects: List[str]
    sections: List[str]
