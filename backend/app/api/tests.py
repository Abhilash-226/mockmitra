import random
import uuid
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone, timedelta
from enum import Enum

# Timezone Constants (IST for Indian Mock Exams)
IST = timezone(timedelta(hours=5, minutes=30))

from pydantic import BaseModel, Field, validator
from beanie import Document, PydanticObjectId, Link
from beanie.operators import In
from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks, Query

from app.core.security import get_current_user, get_optional_user
from app.core.config import settings
from app.models.test import Test, TestAttempt, TestStatus, TestType, TestResponse as TestResponseModel
from app.models.question import Question, QuestionSource, DifficultyLevel
from app.models.blueprint import Blueprint, DifficultyLevel as BlueprintDifficulty, Constraints
from app.schemas.test import TestCreate, TestAttemptResponse, SubmitTestRequest
from app.schemas.question import QuestionInTest
from app.services.question_generator_v2 import get_question_generator_v2
from app.services.blueprint_loader import get_blueprint_loader
from app.services.question_selector import get_question_selector
from app.schemas.exam import ExamConfig
from app.api.exams import load_exam_config


class AIGeneratedQuestion(BaseModel):
    """AI-generated question response model"""
    id: Optional[str] = None
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




@router.post("/generate", response_model=TestAttemptResponse)
async def generate_test(
    test_data: TestCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_optional_user)
):
    """
    Initiate test generation in background.
    Returns the TestAttempt immediately with status 'GENERATING'.
    """
    print(f"DEBUG: generate_test called for {test_data.exam_code}")
    # Load exam config to get details for the shell test
    exam_config = load_exam_config(test_data.exam_code)
    print("DEBUG: Exam config loaded")
    
    # 1. Create the Test shell (without questions initially)
    # Filter sections if requested
    filtered_sections = []
    if test_data.sections:
        target_codes = set(test_data.sections)
        filtered_sections = [s for s in exam_config.sections if s.code in target_codes]
    else:
        filtered_sections = exam_config.sections

    # Topic-wise tests should only allocate questions to sections that contain
    # at least one selected topic.
    if test_data.test_type == TestType.TOPIC_WISE and test_data.topics:
        target_topics = set(test_data.topics)
        filtered_sections = [
            s for s in filtered_sections
            if any(t.code in target_topics for t in (s.topics or []))
        ]
        if not filtered_sections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected topics do not map to any available section for this exam"
            )

    # Use custom values if provided, otherwise fall back to exam_config defaults
    total_questions = test_data.custom_question_count or sum(s.total_questions for s in filtered_sections)
    duration_minutes = test_data.custom_duration_minutes or exam_config.total_duration_minutes
    
    # Adjust per-section counts if custom_question_count is provided
    final_sections = [s.model_dump() for s in filtered_sections]
    if test_data.custom_question_count and len(final_sections) > 0:
        actual_total = sum(s['total_questions'] for s in final_sections)
        if actual_total > 0:
            assigned = 0
            for i, s in enumerate(final_sections):
                if i == len(final_sections) - 1:
                    s['total_questions'] = total_questions - assigned
                else:
                    count = int((s['total_questions'] / actual_total) * total_questions)
                    s['total_questions'] = count
                    assigned += count

    test = Test(
        title=test_data.title,
        exam_code=test_data.exam_code,
        test_type=test_data.test_type,
        total_questions=total_questions,
        total_marks=total_questions,  # Assuming 1 mark per question
        duration_minutes=duration_minutes,
        negative_marking=exam_config.default_negative_marks,
        sections=final_sections,
        question_ids=[] # Will be populated in background
    )
    await test.insert()
    
    # 2. Create the Attempt with GENERATING status
    attempt = TestAttempt(
        user_id=PydanticObjectId(user_id),
        test_id=test.id,
        status=TestStatus.GENERATING,
        started_at=None,
        skipped=test.total_questions
    )
    await attempt.insert()
    
    # 3. Add background task
    background_tasks.add_task(
        process_test_generation, 
        test.id, 
        attempt.id, 
        test_data, 
        exam_config
    )
    
    return attempt


async def process_test_generation(test_id: PydanticObjectId, attempt_id: PydanticObjectId, test_data: TestCreate, exam_config: ExamConfig):
    """Background task to generate questions and update test"""
    from app.models.test import TestType # Local import to ensure it's in scope for background task
    print(f"Background: Starting generation for Test {test_id}...")
    try:
        # Get the target test document to update later
        test = await Test.get(test_id)
        if not test:
            print(f"Error: Test {test_id} not found")
            return
            
        target_question_count = test.total_questions
        question_ids = []
        
        # Iterate through subjects then sections
        for subject in exam_config.subjects:
            if len(question_ids) >= target_question_count:
                break
                
            subject_name = subject.name
            print(f"DEBUG: Processing Subject: {subject_name}")
            
            # Find relevant sections for this subject in the TEST
            # Note: test.sections is a flat list of Section objects from the attempt
            for section_config in subject.sections:
                if len(question_ids) >= target_question_count:
                    break
                    
                section_code = section_config.code
                section_name = section_config.name
                
                # Check if this section is needed for this specific test
                # We matching by code
                section_info = next((s for s in test.sections if s.get('code') == section_code), None)
                if not section_info:
                    continue
                    
                needed_for_section = section_info.get('total_questions', 0)
                if needed_for_section <= 0:
                    continue
                    
                print(f"DEBUG: Processing Section: {section_name} (Code: {section_code}), Need: {needed_for_section}")

                # Determine topic filter (scoped to this section for topic-wise tests)
                topics_filter = test_data.topics if (
                    test_data.test_type == TestType.TOPIC_WISE and test_data.topics
                ) else None
                section_topics_filter = None
                if topics_filter:
                    section_topic_codes = {t.code for t in (section_config.topics or [])}
                    section_topics_filter = [t for t in topics_filter if t in section_topic_codes]
                    # No selected topic belongs to this section; skip it.
                    if not section_topics_filter:
                        continue

                topic_single = (
                    section_topics_filter[0]
                    if section_topics_filter and len(section_topics_filter) == 1
                    else None
                )

                # Determine difficulty filter
                diff_filter = (
                    test_data.difficulty
                    if test_data.difficulty and test_data.difficulty != "mixed"
                    else None
                )

                # ── QuestionSelector: unseen-first DB serve + AI fallback ──
                selector = get_question_selector()
                user_id_str = str(attempt_id)  # use attempt owner; attempt already created above
                # Re-fetch attempt to get user_id
                _attempt = await TestAttempt.get(attempt_id)
                user_id_str = str(_attempt.user_id) if _attempt else str(attempt_id)

                try:
                    selected_questions = await selector.select_questions(
                        user_id=user_id_str,
                        exam_code=test_data.exam_code,
                        section=section_name,
                        topic=topic_single,
                        topics=section_topics_filter,
                        difficulty=diff_filter,
                        count=needed_for_section,
                    )
                except Exception as sel_err:
                    print(f"QuestionSelector error for {section_name}: {sel_err}")
                    selected_questions = []

                for q in selected_questions:
                    question_ids.append(q.id)

                print(
                    f"DEBUG: Section {section_name} — got {len(selected_questions)}/{needed_for_section} questions"
                )



        # Finalize Test and Attempt
        test.question_ids = question_ids
        await test.save()
        
        attempt = await TestAttempt.get(attempt_id)
        if attempt:
            if len(question_ids) >= target_question_count:
                attempt.status = TestStatus.NOT_STARTED
                print(f"Background: Test {test_id} complete. {len(question_ids)} questions added.")
            else:
                attempt.status = TestStatus.ABANDONED
                print(
                    f"Background: Test {test_id} incomplete ({len(question_ids)}/{target_question_count}). Marked ABANDONED for safe retry."
                )
            await attempt.save()

    except Exception as e:
        print(f"Background Generation CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()
        attempt = await TestAttempt.get(attempt_id)
        if attempt:
            attempt.status = TestStatus.ABANDONED
            await attempt.save()


@router.post("/{test_id}/start", response_model=TestAttemptResponse)
async def start_test(
    test_id: str,
    user_id: str = Depends(get_current_user)
):
    """Start a test attempt. Returns a fresh or existing in-progress attempt."""
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # 1. Check for existing attempt for this test/user
    attempt = await TestAttempt.find_one(
        TestAttempt.test_id == PydanticObjectId(test_id),
        TestAttempt.user_id == PydanticObjectId(user_id)
    )
    
    if attempt:
        # 2. If attempt exists, check status
        if attempt.status == TestStatus.COMPLETED:
            # If already completed, maybe they want to start a NEW attempt?
            # For now, let's just create a new one to be safe, or return the completed one.
            # In MockMitra, we usually create a NEW attempt if they want to re-take.
            pass # Fall through to creation if we decide so, but let's just reset for now
            
        elif attempt.status in [TestStatus.NOT_STARTED, TestStatus.GENERATING, TestStatus.ABANDONED]:
            # Reset and start fresh!
            attempt.status = TestStatus.IN_PROGRESS
            attempt.started_at = datetime.now(timezone.utc)
            await attempt.save()
            sys.stderr.write(f"Resetting existing attempt {attempt.id} to IN_PROGRESS with fresh timer\n")
            sys.stderr.flush()
        
        elif attempt.status == TestStatus.IN_PROGRESS:
            # 2b. Check if IN_PROGRESS attempt is stale or inactive
            now = datetime.now(timezone.utc)
            duration_sec = (test.duration_minutes or 180) * 60
            
            # Ensure started_at is aware for calculation
            started_at = attempt.started_at
            if started_at and started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            
            if started_at:
                elapsed_sec = (now - started_at).total_seconds()
                
                # If started more than (duration + 10 mins) ago, OR
                # if 0 questions answered and started more than 5 mins ago
                is_stale = elapsed_sec > (duration_sec + 600)
                has_no_progress = attempt.total_attempted == 0 and elapsed_sec > 300
                
                if is_stale or has_no_progress:
                    attempt.started_at = now
                    await attempt.save()
                    ist_now = now.astimezone(IST).strftime('%Y-%m-%d %I:%M:%S %p')
                    sys.stderr.write(f"[{ist_now} IST] Resetting stale attempt {attempt.id} (Elapsed: {elapsed_sec}s)\n")
                    sys.stderr.flush()
        
        # If it's already IN_PROGRESS and recent, we just return it (it might be a refresh)
    else:
        # 3. Create fresh attempt if none exists
        attempt = TestAttempt(
            user_id=PydanticObjectId(user_id),
            test_id=PydanticObjectId(test_id),
            status=TestStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
            skipped=test.total_questions
        )
        await attempt.insert()
        ist_now = datetime.now(IST).strftime('%Y-%m-%d %I:%M:%S %p')
        sys.stderr.write(f"[{ist_now} IST] Created new attempt {attempt.id} for test {test_id}\n")
        sys.stderr.flush()
    
    # Enrich response with test details
    response = TestAttemptResponse.model_validate(attempt)
    response.test_title = test.title
    response.exam_code = test.exam_code
    response.duration_minutes = test.duration_minutes
    response.total_questions = test.total_questions
    response.sections = test.sections
    return response


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
    user_id: str = Depends(get_current_user)
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
    
    #  Check if test already has pre-generated questions
    if test.question_ids and len(test.question_ids) > 0:
        sys.stderr.write(f"Using {len(test.question_ids)} pre-generated questions for test {test_id}\n")
        sys.stderr.flush()
        
        # Fetch questions from database
        questions = await Question.find(
            In(Question.id, test.question_ids)
        ).to_list()
        
        # Convert to response format
        ai_questions: List[AIGeneratedQuestion] = []
        for q in questions:
            ai_questions.append(AIGeneratedQuestion(
                id=str(q.id),
                question_text=q.question_text,
                options=q.options,
                section=q.section,
                topic=q.topic,
                difficulty=q.difficulty or "medium"
            ))
        
        return AIQuestionsResponse(
            test_id=str(test.id),
            questions=ai_questions,
            total_questions=len(ai_questions)
        )
    
    # If no pre-generated questions, generate on-the-fly
    sys.stderr.write(f"No pre-generated questions found. Generating on-the-fly for test {test_id}\n")
    sys.stderr.flush()
    
    # Get the question generator (V2 - deterministic workflow)
    generator = get_question_generator_v2()
    
    # Load exam config to get section info
    try:
        exam_config = load_exam_config(test.exam_code)
    except Exception:
        exam_config = None
    
    # Generate questions using blueprints
    ai_questions: List[AIGeneratedQuestion] = []
    
    # If we have subjects in exam config, generate per subject and then per section
    if exam_config and exam_config.subjects:
        for subject in exam_config.subjects:
            subject_name = subject.name
            for section in subject.sections:
                # Check if this section is needed for this specific test
                section_info = next((s for s in test.sections if s.get('code') == section.code), None)
                if not section_info:
                    continue
                
                needed_for_section = section_info.get('total_questions', 0)
                if needed_for_section <= 0:
                    continue

                # Use limit if provided, otherwise respect the test's needed count
                section_count = limit if limit else needed_for_section
                section_count = min(section_count, section.total_questions)
                
                section_name = section.name
                print(f"Generating {section_count} questions for {subject_name} > {section_name}...")
                
                # Generate questions for this section (deterministic V2 workflow)
                generated = generator.generate_batch(
                    count=section_count,
                    subject=subject_name,
                    section=section_name,
                    unique_blueprints=True,
                    use_ai_phrasing=use_ai_phrasing
                )
                
                if not generated:
                    # Fallback: try by subject only if section yielded nothing
                    print(f"No questions found for section {section_name}, falling back to subject {subject_name}")
                    generated = generator.generate_batch(
                        count=section_count,
                        subject=subject_name,
                        unique_blueprints=True,
                        use_ai_phrasing=use_ai_phrasing
                    )

                print(f"Generated {len(generated)} questions for {subject_name} > {section_name}")
            
                # Convert to response format (moved INSIDE the loop)
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
            answered_at=datetime.now(timezone.utc)
        )
        responses_to_insert.append(test_response)
    
    # Bulk insert responses
    if responses_to_insert:
        await TestResponseModel.insert_many(responses_to_insert)
    
    # Update attempt
    attempt.status = TestStatus.COMPLETED
    attempt.completed_at = datetime.now(timezone.utc)
    
    # Ensure started_at is aware for calculation (v6.4+ React Router Data API fix)
    started_at = attempt.started_at
    if started_at and started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    
    if started_at:
        attempt.time_taken_seconds = int((attempt.completed_at - started_at).total_seconds())
    else:
        attempt.time_taken_seconds = 0
        
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
    ).sort(-TestAttempt.started_at).limit(50).to_list()
    
    # Fetch test details to populate titles
    test_ids = list(set([a.test_id for a in attempts]))
    tests = await Test.find({"_id": {"$in": test_ids}}).to_list()
    test_map = {t.id: t for t in tests}
    
    response = []
    for attempt in attempts:
        test_info = test_map.get(attempt.test_id)
        # Create response object manually to include extra fields
        resp = TestAttemptResponse.model_validate(attempt)
        if test_info:
            resp.test_title = test_info.title
            resp.exam_code = test_info.exam_code
            resp.duration_minutes = test_info.duration_minutes
            resp.total_questions = test_info.total_questions
            resp.sections = test_info.sections
        response.append(resp)
        
    return response


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


# =============================================================================
# VALIDATION ENDPOINTS
# =============================================================================

class ValidationReportResponse(BaseModel):
    """Response model for validation report"""
    is_valid: bool
    total_questions: int
    expected_questions: int
    error_count: int
    warning_count: int
    section_counts: Dict[str, int]
    expected_section_counts: Dict[str, int]
    issues: List[Dict[str, Any]]
    summary: str


@router.post("/validate-generated", response_model=ValidationReportResponse)
async def validate_generated_questions(
    questions: List[AIGeneratedQuestion],
    expected_total: int = 160,
    user_id: str = Depends(get_optional_user)
):
    """
    Validate a list of generated questions before saving to DB.
    
    This is a PRE-DEPLOYMENT check to catch:
    - Placeholder options
    - Missing correct answers
    - Duplicate options
    - Structural issues
    
    Call this BEFORE publishing a test.
    """
    from app.services.exam_validator import validate_exam
    
    # Convert AIGeneratedQuestion to dict format for validator
    question_dicts = []
    for q in questions:
        options_list = [
            q.options.get("a", ""),
            q.options.get("b", ""),
            q.options.get("c", ""),
            q.options.get("d", ""),
        ]
        question_dicts.append({
            "id": q.id,
            "question_text": q.question_text,
            "options": options_list,
            "correct_answer": options_list[0] if options_list else "",  # First option as placeholder
            "correct_option_index": 0,
            "section": q.section,
            "subject": q.section,
            "topic": q.topic,
            "difficulty": q.difficulty,
        })
    
    # Run validation
    report = validate_exam(
        question_dicts,
        expected_total=expected_total,
        section_distribution={
            "Mathematics": 80,
            "Physics": 40,
            "Chemistry": 40,
        }
    )
    
    # Convert issues to dict
    issues_list = [
        {
            "severity": issue.severity.value,
            "question_id": issue.question_id,
            "question_index": issue.question_index,
            "field": issue.field,
            "message": issue.message,
            "details": issue.details,
        }
        for issue in report.issues
    ]
    
    return ValidationReportResponse(
        is_valid=report.is_valid,
        total_questions=report.total_questions,
        expected_questions=report.expected_questions,
        error_count=report.error_count,
        warning_count=report.warning_count,
        section_counts=report.section_counts,
        expected_section_counts=report.expected_section_counts,
        issues=issues_list,
        summary=report.summary(),
    )


@router.get("/{test_id}/validate", response_model=ValidationReportResponse)
async def validate_test(
    test_id: str,
    user_id: str = Depends(get_optional_user)
):
    """
    Validate an existing test's questions.
    
    Useful for checking test quality after generation.
    """
    from app.services.exam_validator import validate_exam
    
    # Get test
    test = await Test.get(PydanticObjectId(test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get questions
    questions = await Question.find({"_id": {"$in": test.question_ids}}).to_list()
    
    # Convert to dict format
    question_dicts = []
    for q in questions:
        options_list = [
            q.options.get("a", "") if isinstance(q.options, dict) else (q.options[0] if q.options else ""),
            q.options.get("b", "") if isinstance(q.options, dict) else (q.options[1] if len(q.options) > 1 else ""),
            q.options.get("c", "") if isinstance(q.options, dict) else (q.options[2] if len(q.options) > 2 else ""),
            q.options.get("d", "") if isinstance(q.options, dict) else (q.options[3] if len(q.options) > 3 else ""),
        ]
        question_dicts.append({
            "id": str(q.id),
            "question_text": q.question_text,
            "options": options_list,
            "correct_answer": options_list[["a", "b", "c", "d"].index(q.correct_option)] if q.correct_option in ["a", "b", "c", "d"] else "",
            "correct_option_index": ["a", "b", "c", "d"].index(q.correct_option) if q.correct_option in ["a", "b", "c", "d"] else 0,
            "section": q.section,
            "subject": q.section,
            "topic": q.topic,
            "difficulty": str(q.difficulty) if q.difficulty else "medium",
        })
    
    # Run validation
    report = validate_exam(
        question_dicts,
        expected_total=test.total_questions,
        section_distribution={
            "Mathematics": 80,
            "Physics": 40,
            "Chemistry": 40,
        }
    )
    
    # Convert issues to dict
    issues_list = [
        {
            "severity": issue.severity.value,
            "question_id": issue.question_id,
            "question_index": issue.question_index,
            "field": issue.field,
            "message": issue.message,
            "details": issue.details,
        }
        for issue in report.issues
    ]
    
    return ValidationReportResponse(
        is_valid=report.is_valid,
        total_questions=report.total_questions,
        expected_questions=report.expected_questions,
        error_count=report.error_count,
        warning_count=report.warning_count,
        section_counts=report.section_counts,
        expected_section_counts=report.expected_section_counts,
        issues=issues_list,
        summary=report.summary(),
    )