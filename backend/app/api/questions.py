from fastapi import APIRouter, HTTPException, Query
from beanie import PydanticObjectId
from typing import List, Optional

from app.core.security import get_current_user
from app.models.question import Question, DifficultyLevel
from app.schemas.question import QuestionCreate, QuestionResponse

router = APIRouter()


@router.post("/", response_model=QuestionResponse)
async def create_question(question_data: QuestionCreate):
    """Create a new question (admin)"""
    question = Question(**question_data.model_dump())
    await question.insert()
    return question


@router.post("/bulk", response_model=List[QuestionResponse])
async def create_questions_bulk(questions_data: List[QuestionCreate]):
    """Create multiple questions (admin)"""
    questions = [Question(**q.model_dump()) for q in questions_data]
    await Question.insert_many(questions)
    return questions


@router.get("/", response_model=List[QuestionResponse])
async def list_questions(
    exam_code: Optional[str] = None,
    section: Optional[str] = None,
    topic: Optional[str] = None,
    difficulty: Optional[DifficultyLevel] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List questions with filters"""
    # Build query filters
    filters = {}
    if exam_code:
        filters["exam_code"] = exam_code
    if section:
        filters["section"] = section
    if topic:
        filters["topic"] = topic
    if difficulty:
        filters["difficulty"] = difficulty
    
    questions = await Question.find(filters).skip(skip).limit(limit).to_list()
    return questions


@router.get("/stats")
async def get_question_stats(exam_code: Optional[str] = None):
    """Get question bank statistics"""
    pipeline = [
        {"$group": {
            "_id": {"exam_code": "$exam_code", "section": "$section"},
            "count": {"$sum": 1}
        }}
    ]
    
    if exam_code:
        pipeline.insert(0, {"$match": {"exam_code": exam_code}})
    
    results = await Question.aggregate(pipeline).to_list()
    
    return [
        {"exam_code": r["_id"]["exam_code"], "section": r["_id"]["section"], "count": r["count"]}
        for r in results
    ]


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str):
    """Get a specific question"""
    question = await Question.get(PydanticObjectId(question_id))
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return question


@router.delete("/{question_id}")
async def delete_question(question_id: str):
    """Delete a question (admin)"""
    question = await Question.get(PydanticObjectId(question_id))
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    await question.delete()
    
    return {"message": "Question deleted"}
