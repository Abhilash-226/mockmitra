from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from typing import Optional, List
from pydantic import BaseModel
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout

from app.core.security import get_current_user
from app.models.test import TestAttempt, TestStatus, Test
from app.models.user import User
from app.core.config import settings

router = APIRouter()


def _raise_db_unavailable(e: Exception):
    print(f"Database unavailable in analytics endpoint: {e}")
    raise HTTPException(
        status_code=503,
        detail="Database temporarily unavailable. Please retry in a few moments.",
    )


@router.get("/dashboard")
async def get_dashboard_analytics(user_id: str = Depends(get_current_user)):
    """Get user dashboard analytics"""
    uid = PydanticObjectId(user_id)
    try:
        # Fetch only recently completed attempts (capped) instead of all
        attempts = await TestAttempt.find(
            TestAttempt.user_id == uid,
            TestAttempt.status == TestStatus.COMPLETED
        ).sort(-TestAttempt.completed_at).limit(200).to_list()
    except (ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout) as e:
        _raise_db_unavailable(e)
    
    if not attempts:
        return {
            "total_tests": 0,
            "average_score": 0,
            "average_percentage": 0,
            "total_questions_attempted": 0,
            "overall_accuracy": 0,
            "total_time_spent_hours": 0,
            "recent_attempts": []
        }
    
    total_tests = len(attempts)
    total_score = sum(a.score for a in attempts)
    total_percentage = sum(a.percentage for a in attempts)
    total_attempted = sum(a.total_attempted for a in attempts)
    total_correct = sum(a.correct_answers for a in attempts)
    total_time = sum(a.time_taken_seconds or 0 for a in attempts)
    
    return {
        "total_tests": total_tests,
        "average_score": round(total_score / total_tests, 2),
        "average_percentage": round(total_percentage / total_tests, 2),
        "total_questions_attempted": total_attempted,
        "overall_accuracy": round((total_correct / total_attempted) * 100, 2) if total_attempted > 0 else 0,
        "total_time_spent_hours": round(total_time / 3600, 2),
        "recent_attempts": [
            {
                "id": str(a.id),
                "test_id": str(a.test_id),
                "score": a.score,
                "percentage": a.percentage,
                "completed_at": a.completed_at
            }
            for a in attempts[:5]
        ]
    }


@router.get("/performance/{exam_code}")
async def get_exam_performance(
    exam_code: str,
    user_id: str = Depends(get_current_user)
):
    """Get performance analytics for a specific exam"""
    uid = PydanticObjectId(user_id)
    try:
        # Get test IDs for this exam
        tests = await Test.find(Test.exam_code == exam_code).to_list()
    except (ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout) as e:
        _raise_db_unavailable(e)
    test_ids = [t.id for t in tests]
    
    if not test_ids:
        return {
            "exam_code": exam_code,
            "total_attempts": 0,
            "progress": [],
            "best_score": 0,
            "average_score": 0
        }
    
    try:
        # Get attempts for these tests
        attempts = await TestAttempt.find(
            TestAttempt.user_id == uid,
            {"test_id": {"$in": test_ids}},
            TestAttempt.status == TestStatus.COMPLETED
        ).sort(+TestAttempt.completed_at).to_list()
    except (ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout) as e:
        _raise_db_unavailable(e)
    
    if not attempts:
        return {
            "exam_code": exam_code,
            "total_attempts": 0,
            "progress": [],
            "best_score": 0,
            "average_score": 0
        }
    
    return {
        "exam_code": exam_code,
        "total_attempts": len(attempts),
        "progress": [
            {
                "attempt_number": i + 1,
                "score": a.score,
                "percentage": a.percentage,
                "date": a.completed_at
            }
            for i, a in enumerate(attempts)
        ],
        "best_score": max(a.score for a in attempts),
        "average_score": round(sum(a.score for a in attempts) / len(attempts), 2)
    }


@router.get("/attempt/{attempt_id}")
async def get_attempt_analytics(
    attempt_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get detailed analytics for a specific attempt"""
    from app.models.test import TestResponse as TestResponseModel
    from app.models.question import Question
    
    uid = PydanticObjectId(user_id)
    aid = PydanticObjectId(attempt_id)
    
    try:
        # Get attempt
        attempt = await TestAttempt.find_one(
            TestAttempt.id == aid,
            TestAttempt.user_id == uid
        )
    except (ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout) as e:
        _raise_db_unavailable(e)
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    try:
        # Get responses
        responses = await TestResponseModel.find(
            TestResponseModel.attempt_id == aid
        ).to_list()

        # Build a map of responses keyed by question_id for quick lookup
        response_map = {str(r.question_id): r for r in responses}

        # Fetch full question documents
        question_ids = [r.question_id for r in responses]
        questions_docs = await Question.find(
            {"_id": {"$in": question_ids}}
        ).to_list()

        # Build questions list in response order
        question_doc_map = {str(q.id): q for q in questions_docs}
        questions_list = []
        for idx, r in enumerate(responses):
            qid = str(r.question_id)
            q = question_doc_map.get(qid)
            if not q:
                continue
            # options is a dict like {"a": "...", "b": "...", ...}
            # Convert to list of {key, text} for the frontend
            options_list = [{"key": k, "text": v} for k, v in q.options.items()]
            questions_list.append({
                "id": qid,
                "question_text": q.question_text,
                "options": options_list,
                "correct_answer": q.correct_option,
                "selected_option": r.selected_option,
                "is_correct": r.is_correct,
                "topic": q.topic or "General",
                "section": q.section or "General",
                "difficulty": q.difficulty.value if q.difficulty else "medium",
                "solution": q.explanation or "No explanation available",
                "time_spent": r.time_spent_seconds,
                "image": q.image,
            })

        # Calculate time analysis
        time_per_question = [r.time_spent_seconds for r in responses if r.time_spent_seconds]

        # Fetch test for title/marks
        test_doc = await Test.get(attempt.test_id)
    except (ServerSelectionTimeoutError, AutoReconnect, NetworkTimeout) as e:
        _raise_db_unavailable(e)
    test_name = test_doc.title if test_doc else "Test"
    max_score = test_doc.total_marks if test_doc else (attempt.total_attempted + attempt.skipped)

    return {
        "attempt_id": str(attempt_id),
        "test_name": test_name,
        "score": attempt.score,
        "max_score": max_score,
        "percentage": attempt.percentage,
        "total_questions": attempt.total_attempted + attempt.skipped,
        "correct": attempt.correct_answers,
        "wrong": attempt.wrong_answers,
        "skipped": attempt.skipped,
        "time_taken_seconds": attempt.time_taken_seconds,
        "average_time_per_question": round(sum(time_per_question) / len(time_per_question), 2) if time_per_question else 0,
        "section_results": attempt.section_results,
        "questions": questions_list,
        "responses": [
            {
                "question_id": str(r.question_id),
                "selected_option": r.selected_option,
                "is_correct": r.is_correct,
                "time_spent": r.time_spent_seconds,
                "topic": question_doc_map.get(str(r.question_id), {}).topic if question_doc_map.get(str(r.question_id)) else "General",
            }
            for r in responses
        ]
    }


# ── Solution generation ────────────────────────────────────────────────────────

class SolutionRequest(BaseModel):
    question_text: str
    options: List[dict]          # [{"value": "a", "text": "..."}]
    correct_answer: str          # option value, e.g. "b"
    topic: Optional[str] = None
    section: Optional[str] = None


@router.post("/generate-solution")
async def generate_solution(
    body: SolutionRequest,
    user_id: str = Depends(get_current_user)
):
    """Generate a step-by-step solution using Groq LLM."""
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    # Find the correct option text
    correct_text = body.correct_answer
    option_labels = ["A", "B", "C", "D", "E", "F"]
    options_str_parts = []
    for idx, opt in enumerate(body.options):
        label = option_labels[idx] if idx < len(option_labels) else str(idx + 1)
        text = opt.get("text", "")
        is_correct = opt.get("value") == body.correct_answer
        if is_correct:
            correct_text = f"{label}. {text}"
        options_str_parts.append(f"{label}. {text}")
    options_str = "\n".join(options_str_parts)

    context = ""
    if body.section or body.topic:
        context = f"Subject/Section: {body.section or ''}  Topic: {body.topic or ''}\n"

    prompt = f"""You are an expert tutor helping a student understand a multiple-choice exam question.

{context}Question:
{body.question_text}

Options:
{options_str}

Correct Answer: {correct_text}

Provide a clear, concise step-by-step solution that:
1. Identifies the key concept being tested
2. Shows the logical/mathematical working clearly
3. Explains why the correct answer is right
4. Briefly explains why the other options are incorrect (if helpful)

Use LaTeX for all mathematical expressions (wrap in $...$ for inline, $$...$$ for display).
Keep the solution educational but concise (aim for 150-300 words)."""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=600,
        )
        solution_text = response.choices[0].message.content.strip()
        return {"solution": solution_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solution generation failed: {e}")
