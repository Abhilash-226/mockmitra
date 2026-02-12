from fastapi import APIRouter, Depends, HTTPException, status, Header
from beanie import PydanticObjectId
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.test import Test, TestAttempt, TestResponse as TestResponseModel, TestStatus
from app.models.question import Question, QuestionSource, DifficultyLevel
from app.schemas.test import TestCreate, TestResponse, TestAttemptResponse, SubmitTestRequest
from app.schemas.question import QuestionInTest
from app.api.exams import load_exam_config
from app.services.question_generator_v2 import get_question_generator_v2
from app.models.blueprint import Blueprint, DifficultyLevel as BlueprintDifficulty, Constraints
import random


class AIGeneratedQuestion(BaseModel):
    """AI-generated question response model"""
    id: str
    question_text: str
    options: Dict[str, str]  # {"a": "...", "b": "...", "c": "...", "d": "..."}
    section: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = None


class AIQuestionsResponse(BaseModel):
    """Response containing AI-generated questions"""
    test_id: str
    questions: List[AIGeneratedQuestion]
    total_questions: int

router = APIRouter()

# Fixed test user ObjectId for development (24 hex chars)
DEV_USER_ID = "000000000000000000000001"


async def get_optional_user(authorization: Optional[str] = Header(None)) -> str:
    """Get user ID from token, or return a test user ID for development"""
    if authorization and authorization.startswith("Bearer "):
        from app.core.security import decode_token
        token = authorization.split(" ")[1]
        payload = decode_token(token)
        if payload and payload.get("sub"):
            return payload.get("sub")
    # Return a fixed test user ObjectId for development
    return DEV_USER_ID


@router.post("/generate", response_model=TestResponse)
async def generate_test(
    test_data: TestCreate,
    user_id: str = Depends(get_optional_user)
):
    """Generate a new test based on exam configuration"""
    # Load exam config
    exam_config = load_exam_config(test_data.exam_code)
    
    # Get questions for each section
    question_ids = []
    generator = get_question_generator_v2()
    
    for section in exam_config.sections:
        # Query questions for this section
        section_questions = await Question.find(
            Question.exam_code == test_data.exam_code,
            Question.section == section.code
        ).to_list()
        
        needed = section.total_questions
        
        # Randomly select required number of questions
        if len(section_questions) >= needed:
            selected = random.sample(section_questions, needed)
            question_ids.extend([q.id for q in selected])
        else:
            # Use available questions first
            question_ids.extend([q.id for q in section_questions])
            shortage = needed - len(section_questions)
            
            # Generate missing questions with LLM
            if generator.llm_client and shortage > 0:
                for topic in section.topics[:shortage]:
                    topic_name = topic.name if hasattr(topic, 'name') else str(topic)
                    topic_code = topic.code if hasattr(topic, 'code') else topic_name.lower().replace(' ', '_')
                    
                    blueprint = Blueprint(
                        id=f"{section.code}_{topic_code}_GEN",
                        exam=test_data.exam_code.upper(),
                        subject=section.name,
                        chapter=topic_name,
                        concept=topic_name,
                        template_variants=[f"Question about {topic_name}"],
                        difficulty_level=BlueprintDifficulty.MODERATE,
                        answer_type="numeric",
                        answer_unit="dimensionless",
                        constraints=Constraints(steps=2, expected_time_sec=90),
                        tags=[section.code, topic_code],
                    )
                    
                    try:
                        gen_q = generator.generate_from_blueprint(blueprint, use_ai_phrasing=False)
                        if gen_q is None:
                            continue
                        
                        # Store generated question in DB
                        db_question = Question(
                            question_text=gen_q.question_text,
                            options={
                                "a": gen_q.options[0] if len(gen_q.options) > 0 else "A",
                                "b": gen_q.options[1] if len(gen_q.options) > 1 else "B",
                                "c": gen_q.options[2] if len(gen_q.options) > 2 else "C",
                                "d": gen_q.options[3] if len(gen_q.options) > 3 else "D",
                            },
                            correct_option=["a", "b", "c", "d"][gen_q.correct_option_index],
                            explanation=gen_q.solution,
                            exam_code=test_data.exam_code,
                            section=section.code,
                            topic=topic_code,
                            difficulty=DifficultyLevel.MEDIUM,
                            source=QuestionSource.AI_GENERATED,
                        )
                        await db_question.insert()
                        question_ids.append(db_question.id)
                    except Exception as e:
                        print(f"Failed to generate question for {topic_name}: {e}")
    
    # Create test
    test = Test(
        title=test_data.title,
        exam_code=test_data.exam_code,
        test_type=test_data.test_type,
        total_questions=exam_config.total_questions,
        total_marks=exam_config.total_marks,
        duration_minutes=exam_config.total_duration_minutes,
        negative_marking=exam_config.default_negative_marks,
        sections=[s.model_dump() for s in exam_config.sections],
        question_ids=question_ids
    )
    
    await test.insert()
    return test


@router.post("/{test_id}/start", response_model=TestAttemptResponse)
async def start_test(
    test_id: str,
    user_id: str = Depends(get_optional_user)
):
    """Start a test attempt"""
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Check for existing in-progress attempt - return it instead of error
    existing = await TestAttempt.find_one(
        TestAttempt.test_id == PydanticObjectId(test_id),
        TestAttempt.user_id == PydanticObjectId(user_id),
        TestAttempt.status == TestStatus.IN_PROGRESS
    )
    if existing:
        # Return existing attempt instead of throwing error
        return existing
    
    # Create attempt
    attempt = TestAttempt(
        user_id=PydanticObjectId(user_id),
        test_id=PydanticObjectId(test_id),
        status=TestStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        skipped=test.total_questions
    )
    
    await attempt.insert()
    return attempt


@router.get("/{test_id}/questions", response_model=List[QuestionInTest])
async def get_test_questions(
    test_id: str,
    user_id: str = Depends(get_optional_user)
):
    """Get questions for a test (without answers)"""
    # Verify user has an active attempt
    attempt = await TestAttempt.find_one(
        TestAttempt.test_id == PydanticObjectId(test_id),
        TestAttempt.user_id == PydanticObjectId(user_id),
        TestAttempt.status == TestStatus.IN_PROGRESS
    )
    if not attempt:
        raise HTTPException(status_code=403, detail="No active test attempt")
    
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get questions
    questions = await Question.find({"_id": {"$in": test.question_ids}}).to_list()
    
    # Return questions without correct answers
    return [QuestionInTest.model_validate(q) for q in questions]


@router.get("/{test_id}/ai-questions", response_model=AIQuestionsResponse)
async def get_ai_generated_questions(
    test_id: str,
    limit: Optional[int] = None,
    use_ai_phrasing: bool = False,
    user_id: str = Depends(get_optional_user)
):
    """Get deterministically-generated questions for a test.
    
    Uses the V2 deterministic workflow:
    - Variables sampled within blueprint constraints
    - Answer computed by code (NOT AI)
    - Distractors from blueprint formulas (common student errors)
    - AI only used for phrasing improvement (optional)
    
    Args:
        test_id: The test ID
        limit: Optional limit on number of questions per section. 
               Default is None (use full count from exam config for full mock).
        use_ai_phrasing: Whether to use AI for question text phrasing.
                         Default is False for fast generation.
                         Set to True for improved grammar (slower).
    """
    # Verify user has an active attempt
    attempt = await TestAttempt.find_one(
        TestAttempt.test_id == PydanticObjectId(test_id),
        TestAttempt.user_id == PydanticObjectId(user_id),
        TestAttempt.status == TestStatus.IN_PROGRESS
    )
    if not attempt:
        raise HTTPException(status_code=403, detail="No active test attempt. Start the test first.")
    
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get the question generator (V2 - deterministic workflow)
    generator = get_question_generator_v2()
    
    # Load exam config to get section info
    try:
        exam_config = load_exam_config(test.exam_code)
    except Exception:
        exam_config = None
    
    # Generate questions using blueprints
    ai_questions: List[AIGeneratedQuestion] = []
    
    # If we have sections in exam config, generate per section
    if exam_config and exam_config.sections:
        for section in exam_config.sections:
            # Use limit if provided, otherwise use full section count for complete mock
            section_count = limit if limit else section.total_questions
            section_count = min(section_count, section.total_questions)
            
            subject_name = section.name  # e.g., "Mathematics", "Physics", "Chemistry"
            print(f"Generating {section_count} questions for {subject_name}...")
            
            # Generate questions for this section (deterministic V2 workflow)
            generated = generator.generate_batch(
                count=section_count,
                subject=subject_name,
                unique_blueprints=True,
                use_ai_phrasing=use_ai_phrasing
            )
            print(f"Generated {len(generated)} questions for {subject_name}")
            
            # Convert to response format
            for q in generated:
                options_dict = {
                    "a": q.options[0] if len(q.options) > 0 else "Option A",
                    "b": q.options[1] if len(q.options) > 1 else "Option B",
                    "c": q.options[2] if len(q.options) > 2 else "Option C",
                    "d": q.options[3] if len(q.options) > 3 else "Option D",
                }
                ai_questions.append(AIGeneratedQuestion(
                    id=q.id,
                    question_text=q.question_text,
                    options=options_dict,
                    section=section.code,
                    topic=q.chapter,
                    difficulty=str(q.difficulty_level) if q.difficulty_level else "moderate"
                ))
    else:
        # No sections - generate generic questions using full count
        question_count = limit if limit else test.total_questions
        print(f"Generating {question_count} questions (no sections)...")
        
        all_questions = generator.generate_batch(
            count=question_count,
            unique_blueprints=True,
            use_ai_phrasing=use_ai_phrasing
        )
        print(f"Generated {len(all_questions)} questions")
        
        for q in all_questions:
            options_dict = {
                "a": q.options[0] if len(q.options) > 0 else "Option A",
                "b": q.options[1] if len(q.options) > 1 else "Option B",
                "c": q.options[2] if len(q.options) > 2 else "Option C",
                "d": q.options[3] if len(q.options) > 3 else "Option D",
            }
            ai_questions.append(AIGeneratedQuestion(
                id=q.id,
                question_text=q.question_text,
                options=options_dict,
                section=q.subject.lower() if q.subject else None,
                topic=q.chapter,
                difficulty=str(q.difficulty_level) if q.difficulty_level else "moderate"
            ))
    
    # Store question IDs in attempt for later evaluation (optional)
    # This would require modifying the TestAttempt model
    
    return AIQuestionsResponse(
        test_id=str(test.id),
        questions=ai_questions,
        total_questions=len(ai_questions)
    )


@router.post("/{test_id}/submit", response_model=TestAttemptResponse)
async def submit_test(
    test_id: str,
    submission: SubmitTestRequest,
    user_id: str = Depends(get_optional_user)
):
    """Submit test and get results"""
    # Get attempt
    attempt = await TestAttempt.find_one(
        TestAttempt.test_id == PydanticObjectId(test_id),
        TestAttempt.user_id == PydanticObjectId(user_id),
        TestAttempt.status == TestStatus.IN_PROGRESS
    )
    
    if not attempt:
        raise HTTPException(status_code=404, detail="No active test attempt")
    
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    
    # Get correct answers
    questions_list = await Question.find({"_id": {"$in": test.question_ids}}).to_list()
    questions = {str(q.id): q for q in questions_list}
    
    # Evaluate responses
    correct = 0
    wrong = 0
    skipped = 0
    score = 0.0
    
    responses_to_insert = []
    
    for response in submission.responses:
        question = questions.get(str(response.question_id))
        if not question:
            continue
        
        is_correct = None
        if response.selected_option is None:
            skipped += 1
        elif response.selected_option == question.correct_option:
            correct += 1
            is_correct = True
            score += test.total_marks / test.total_questions
        else:
            wrong += 1
            is_correct = False
            score -= test.negative_marking
        
        # Prepare response for bulk insert
        test_response = TestResponseModel(
            attempt_id=attempt.id,
            question_id=PydanticObjectId(response.question_id),
            selected_option=response.selected_option,
            is_correct=is_correct,
            is_marked_for_review=response.is_marked_for_review,
            time_spent_seconds=response.time_spent_seconds,
            answered_at=datetime.utcnow()
        )
        responses_to_insert.append(test_response)
    
    # Bulk insert responses
    if responses_to_insert:
        await TestResponseModel.insert_many(responses_to_insert)
    
    # Update attempt
    attempt.status = TestStatus.COMPLETED
    attempt.completed_at = datetime.utcnow()
    attempt.time_taken_seconds = int((attempt.completed_at - attempt.started_at).total_seconds())
    attempt.total_attempted = correct + wrong
    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.skipped = skipped
    attempt.score = max(0, score)
    attempt.percentage = (correct / test.total_questions) * 100 if test.total_questions > 0 else 0
    
    await attempt.save()
    
    return attempt


@router.get("/history", response_model=List[TestAttemptResponse])
async def get_test_history(user_id: str = Depends(get_current_user)):
    """Get user's test history"""
    attempts = await TestAttempt.find(
        TestAttempt.user_id == PydanticObjectId(user_id)
    ).sort(-TestAttempt.started_at).to_list()
    
    return attempts


@router.get("/{test_id}/review")
async def get_test_review(
    test_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get test review with solutions after completion"""
    # Verify user has a completed attempt
    attempt = await TestAttempt.find_one(
        TestAttempt.test_id == PydanticObjectId(test_id),
        TestAttempt.user_id == PydanticObjectId(user_id),
        TestAttempt.status == TestStatus.COMPLETED
    )
    if not attempt:
        raise HTTPException(
            status_code=403,
            detail="No completed test attempt found. Complete the test first."
        )
    
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get all questions with solutions
    questions = await Question.find({"_id": {"$in": test.question_ids}}).to_list()
    
    # Get user's responses
    responses = await TestResponseModel.find(
        TestResponseModel.attempt_id == attempt.id
    ).to_list()
    response_map = {str(r.question_id): r for r in responses}
    
    # Build review data
    review_items = []
    for q in questions:
        user_response = response_map.get(str(q.id))
        review_items.append({
            "question_id": str(q.id),
            "question_text": q.question_text,
            "options": q.options,
            "correct_option": q.correct_option,
            "user_selected": user_response.selected_option if user_response else None,
            "is_correct": user_response.is_correct if user_response else None,
            "time_spent_seconds": user_response.time_spent_seconds if user_response else 0,
            "solution": q.explanation or "Solution not available",
            "topic": q.topic,
            "difficulty": q.difficulty,
        })
    
    return {
        "test_id": str(test.id),
        "attempt_id": str(attempt.id),
        "score": attempt.score,
        "percentage": attempt.percentage,
        "correct_answers": attempt.correct_answers,
        "wrong_answers": attempt.wrong_answers,
        "skipped": attempt.skipped,
        "time_taken_seconds": attempt.time_taken_seconds,
        "questions": review_items,
    }
