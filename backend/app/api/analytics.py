from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from typing import Optional

from app.core.security import get_current_user
from app.models.test import TestAttempt, TestStatus, Test
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_analytics(user_id: str = Depends(get_current_user)):
    """Get user dashboard analytics"""
    uid = PydanticObjectId(user_id)
    
    # Get all completed attempts
    attempts = await TestAttempt.find(
        TestAttempt.user_id == uid,
        TestAttempt.status == TestStatus.COMPLETED
    ).to_list()
    
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
            for a in sorted(attempts, key=lambda x: x.completed_at or x.started_at, reverse=True)[:5]
        ]
    }


@router.get("/performance/{exam_code}")
async def get_exam_performance(
    exam_code: str,
    user_id: str = Depends(get_current_user)
):
    """Get performance analytics for a specific exam"""
    uid = PydanticObjectId(user_id)
    
    # Get test IDs for this exam
    tests = await Test.find(Test.exam_code == exam_code).to_list()
    test_ids = [t.id for t in tests]
    
    if not test_ids:
        return {
            "exam_code": exam_code,
            "total_attempts": 0,
            "progress": [],
            "best_score": 0,
            "average_score": 0
        }
    
    # Get attempts for these tests
    attempts = await TestAttempt.find(
        TestAttempt.user_id == uid,
        {"test_id": {"$in": test_ids}},
        TestAttempt.status == TestStatus.COMPLETED
    ).sort(+TestAttempt.completed_at).to_list()
    
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
    
    uid = PydanticObjectId(user_id)
    aid = PydanticObjectId(attempt_id)
    
    # Get attempt
    attempt = await TestAttempt.find_one(
        TestAttempt.id == aid,
        TestAttempt.user_id == uid
    )
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    # Get responses
    responses = await TestResponseModel.find(
        TestResponseModel.attempt_id == aid
    ).to_list()
    
    # Calculate time analysis
    time_per_question = [r.time_spent_seconds for r in responses if r.time_spent_seconds]
    
    return {
        "attempt_id": str(attempt_id),
        "score": attempt.score,
        "percentage": attempt.percentage,
        "total_questions": attempt.total_attempted + attempt.skipped,
        "correct": attempt.correct_answers,
        "wrong": attempt.wrong_answers,
        "skipped": attempt.skipped,
        "time_taken_seconds": attempt.time_taken_seconds,
        "average_time_per_question": round(sum(time_per_question) / len(time_per_question), 2) if time_per_question else 0,
        "section_results": attempt.section_results,
        "responses": [
            {
                "question_id": str(r.question_id),
                "selected_option": r.selected_option,
                "is_correct": r.is_correct,
                "time_spent": r.time_spent_seconds
            }
            for r in responses
        ]
    }
