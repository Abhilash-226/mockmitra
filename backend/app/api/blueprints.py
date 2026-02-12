"""
Blueprint and Question Generation API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.blueprint import DifficultyLevel, GeneratedQuestion
from app.services import (
    get_blueprint_loader, 
    reload_blueprints
)
from app.services.question_generator_v2 import get_question_generator_v2


router = APIRouter(tags=["blueprints"])


# ============================================
# Request/Response Models
# ============================================

class BlueprintSummary(BaseModel):
    """Summary of a blueprint for listing."""
    id: str
    exam: Optional[str] = None
    subject: str
    unit: Optional[str] = None
    chapter: str
    concept: Optional[str] = None
    difficulty_level: Optional[str] = None
    tags: List[str] = []


class BlueprintStatistics(BaseModel):
    """Statistics about loaded blueprints."""
    total_blueprints: int
    by_exam: Dict[str, int]
    by_subject: Dict[str, int]
    by_difficulty: Dict[str, int]
    exams: List[str]
    subjects: List[str]


class GenerateRequest(BaseModel):
    """Request to generate questions."""
    count: int = Field(default=1, ge=1, le=100)
    exam: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    unit: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    unique_blueprints: bool = True


class GenerateTestRequest(BaseModel):
    """Request to generate a full test."""
    distribution: Dict[str, int] = Field(
        ...,
        description="Subject to question count mapping",
        example={"Mathematics": 40, "Physics": 40, "Chemistry": 40}
    )
    difficulty_mix: Optional[Dict[str, float]] = Field(
        default=None,
        description="Difficulty to percentage mapping",
        example={"easy": 0.3, "moderate": 0.5, "hard": 0.2}
    )


class QuestionResponse(BaseModel):
    """Response for a generated question."""
    id: str
    blueprint_id: str
    question_text: str
    options: List[str]
    correct_answer: str
    correct_option_index: int
    solution: Optional[str] = None
    difficulty_level: str
    subject: str
    chapter: str
    concept: Optional[str] = None
    tags: List[str] = []


# ============================================
# Blueprint Endpoints
# ============================================

@router.get("/", response_model=List[BlueprintSummary])
async def list_blueprints(
    exam: Optional[str] = Query(None, description="Filter by exam (e.g., TS_EAMCET)"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    chapter: Optional[str] = Query(None, description="Filter by chapter"),
    unit: Optional[str] = Query(None, description="Filter by unit"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results")
):
    """
    List available blueprints with optional filters.
    """
    loader = get_blueprint_loader()
    
    difficulty_level = None
    if difficulty:
        try:
            difficulty_level = DifficultyLevel(difficulty.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid difficulty: {difficulty}")
    
    tags = [tag] if tag else None
    
    blueprints = loader.query_blueprints(
        exam=exam,
        subject=subject,
        chapter=chapter,
        unit=unit,
        difficulty=difficulty_level,
        tags=tags,
        limit=limit
    )
    
    return [
        BlueprintSummary(
            id=bp.id,
            exam=bp.exam,
            subject=bp.subject,
            unit=bp.unit,
            chapter=bp.chapter,
            concept=bp.concept,
            difficulty_level=bp.difficulty_level.value if bp.difficulty_level else None,
            tags=bp.tags or []
        )
        for bp in blueprints
    ]


@router.get("/statistics", response_model=BlueprintStatistics)
async def get_statistics():
    """
    Get statistics about loaded blueprints.
    """
    loader = get_blueprint_loader()
    stats = loader.get_statistics()
    return BlueprintStatistics(**stats)


@router.get("/subjects")
async def get_subjects() -> List[str]:
    """
    Get list of available subjects.
    """
    loader = get_blueprint_loader()
    return loader.get_subjects()


@router.get("/exams")
async def get_exams() -> List[str]:
    """
    Get list of available exams.
    """
    loader = get_blueprint_loader()
    return loader.get_exams()


@router.get("/chapters/{subject}")
async def get_chapters(subject: str) -> List[str]:
    """
    Get list of chapters for a subject.
    """
    loader = get_blueprint_loader()
    return loader.get_chapters_by_subject(subject)


@router.get("/units/{subject}")
async def get_units(subject: str) -> List[str]:
    """
    Get list of units for a subject.
    """
    loader = get_blueprint_loader()
    return loader.get_units_by_subject(subject)


@router.post("/reload")
async def reload_all_blueprints():
    """
    Reload all blueprints from YAML files.
    """
    count = reload_blueprints()
    return {"message": f"Reloaded {count} blueprints"}


@router.get("/{blueprint_id}")
async def get_blueprint(blueprint_id: str):
    """
    Get details of a specific blueprint.
    """
    loader = get_blueprint_loader()
    blueprint = loader.get_blueprint(blueprint_id)
    
    if blueprint is None:
        raise HTTPException(404, f"Blueprint not found: {blueprint_id}")
    
    return blueprint.model_dump()


# ============================================
# Question Generation Endpoints
# ============================================

@router.post("/generate", response_model=List[QuestionResponse])
async def generate_questions(request: GenerateRequest):
    """
    Generate questions based on criteria.
    """
    generator = get_question_generator_v2()
    
    difficulty = None
    if request.difficulty:
        try:
            difficulty = DifficultyLevel(request.difficulty.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid difficulty: {request.difficulty}")
    
    questions = generator.generate_batch(
        count=request.count,
        subject=request.subject,
        chapter=request.chapter,
        difficulty=difficulty,
        tags=request.tags,
        unique_blueprints=request.unique_blueprints
    )
    
    return [
        QuestionResponse(
            id=q.id,
            blueprint_id=q.blueprint_id,
            question_text=q.question_text,
            options=q.options,
            correct_answer=q.correct_answer,
            correct_option_index=q.correct_option_index,
            solution=q.solution,
            difficulty_level=q.difficulty_level.value if q.difficulty_level else "moderate",
            subject=q.subject,
            chapter=q.chapter,
            concept=q.concept,
            tags=q.tags
        )
        for q in questions
    ]


@router.post("/generate-test", response_model=List[QuestionResponse])
async def generate_test(request: GenerateTestRequest):
    """
    Generate a full test with subject distribution.
    """
    generator = get_question_generator_v2()
    
    questions = generator.generate_test(
        distribution=request.distribution,
        difficulty_mix=request.difficulty_mix
    )
    
    return [
        QuestionResponse(
            id=q.id,
            blueprint_id=q.blueprint_id,
            question_text=q.question_text,
            options=q.options,
            correct_answer=q.correct_answer,
            correct_option_index=q.correct_option_index,
            solution=q.solution,
            difficulty_level=q.difficulty_level.value if q.difficulty_level else "moderate",
            subject=q.subject,
            chapter=q.chapter,
            concept=q.concept,
            tags=q.tags
        )
        for q in questions
    ]


@router.get("/generate/{blueprint_id}", response_model=QuestionResponse)
async def generate_from_blueprint(
    blueprint_id: str,
    seed: Optional[int] = Query(None, description="Random seed for reproducibility")
):
    """
    Generate a question from a specific blueprint.
    """
    generator = get_question_generator_v2()
    
    question = generator.generate_by_id(blueprint_id, seed=seed)
    
    if question is None:
        raise HTTPException(404, f"Blueprint not found: {blueprint_id}")
    
    return QuestionResponse(
        id=question.id,
        blueprint_id=question.blueprint_id,
        question_text=question.question_text,
        options=question.options,
        correct_answer=question.correct_answer,
        correct_option_index=question.correct_option_index,
        solution=question.solution,
        difficulty_level=question.difficulty_level.value if question.difficulty_level else "moderate",
        subject=question.subject,
        chapter=question.chapter,
        concept=question.concept,
        tags=question.tags
    )
