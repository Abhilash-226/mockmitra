"""
Configuration for PYQ Extractor.
Stores API keys and exam-specific settings.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent  # PYQS folder
EXAMS_DIR = BASE_DIR / "exams"
BACKEND_PYQ_DIR = BASE_DIR.parent / "backend" / "pyq_papers"

# API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCB7CHR6WRi1-Bs3qHmIb2cBdjUw5ekuzc")


@dataclass
class ExamConfig:
    """Configuration for a specific exam type."""
    code: str  # e.g., "ts_eamcet"
    name: str  # e.g., "TS EAMCET"
    
    # Section configuration
    sections: List[Dict[str, str]] = field(default_factory=list)
    # e.g., [{"code": "MAT", "name": "Mathematics"}, ...]
    
    # Question distribution per section (expected counts)
    section_questions: Dict[str, int] = field(default_factory=dict)
    # e.g., {"MAT": 80, "PHY": 40, "CHE": 40}
    
    # Exam metadata
    duration_minutes: int = 180
    marks_per_question: int = 1
    negative_marks: float = 0
    
    # Pattern hints for AI
    question_pattern: str = ""
    language: str = "English"
    has_bilingual: bool = False  # Telugu/Hindi alongside English
    
    @property
    def pdfs_dir(self) -> Path:
        return EXAMS_DIR / self.code / "pdfs"
    
    @property
    def extracted_dir(self) -> Path:
        return EXAMS_DIR / self.code / "extracted"
    
    @property
    def backend_dir(self) -> Path:
        return BACKEND_PYQ_DIR / self.code
    
    def ensure_dirs(self):
        """Create necessary directories if they don't exist."""
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        self.backend_dir.mkdir(parents=True, exist_ok=True)


# Pre-defined exam configurations
EXAM_CONFIGS: Dict[str, ExamConfig] = {
    "ts_eamcet": ExamConfig(
        code="ts_eamcet",
        name="TS EAMCET",
        sections=[
            {"code": "MAT", "name": "Mathematics"},
            {"code": "PHY", "name": "Physics"},
            {"code": "CHE", "name": "Chemistry"},
        ],
        section_questions={"MAT": 80, "PHY": 40, "CHE": 40},
        duration_minutes=180,
        marks_per_question=1,
        negative_marks=0,
        question_pattern="MCQ with 4 options (1-4 or A-D)",
        language="English",
        has_bilingual=True,  # Has Telugu alongside English
    ),
    
    # Future exams can be added here
    # "jee_main": ExamConfig(...),
    # "neet": ExamConfig(...),
}


def get_exam_config(exam_code: str) -> ExamConfig:
    """Get configuration for an exam by its code."""
    if exam_code not in EXAM_CONFIGS:
        raise ValueError(f"Unknown exam: {exam_code}. Available: {list(EXAM_CONFIGS.keys())}")
    return EXAM_CONFIGS[exam_code]


def list_available_exams() -> List[str]:
    """List all configured exam codes."""
    return list(EXAM_CONFIGS.keys())
