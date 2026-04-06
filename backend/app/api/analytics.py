from fastapi import APIRouter, Depends, HTTPException
from beanie import PydanticObjectId
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import hashlib
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

        # Some attempts may contain multiple response rows per question
        # (autosave + submit). Keep the latest one per question for analysis UI.
        latest_response_by_question: dict[str, TestResponseModel] = {}
        for r in responses:
            qid = str(r.question_id)
            prev = latest_response_by_question.get(qid)
            if not prev:
                latest_response_by_question[qid] = r
                continue

            prev_ts = prev.answered_at or datetime.min.replace(tzinfo=timezone.utc)
            curr_ts = r.answered_at or datetime.min.replace(tzinfo=timezone.utc)
            if curr_ts >= prev_ts:
                latest_response_by_question[qid] = r

        unique_responses = list(latest_response_by_question.values())

        # Build a map of responses keyed by question_id for quick lookup
        response_map = {str(r.question_id): r for r in unique_responses}

        # Fetch full question documents
        question_ids = [r.question_id for r in unique_responses]
        questions_docs = await Question.find(
            {"_id": {"$in": question_ids}}
        ).to_list()

        # Build questions list in response order
        question_doc_map = {str(q.id): q for q in questions_docs}
        questions_list = []
        for idx, r in enumerate(unique_responses):
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
                "paper_id": q.source_paper_id,
                "question_number": q.source_question_number,
            })

        # Calculate time analysis
        time_per_question = [r.time_spent_seconds for r in unique_responses if r.time_spent_seconds]

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
            for r in unique_responses
        ]
    }


# ── Solution generation ────────────────────────────────────────────────────────

class SolutionRequest(BaseModel):
    question_id: Optional[str] = None
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
    """Generate a step-by-step solution using Gemini."""
    from app.models.question import Question
    from app.models.solution_cache import SolutionCache

    def _is_acceptable_cached_solution(text: str) -> bool:
        if not text:
            return False
        stripped = text.strip()
        words = len(stripped.split())
        # If model formatting exists, require section markers.
        if "1) Concept Tested" in stripped:
            required = [
                "1) Concept Tested",
                "2) Step-by-Step Working",
                "3) Evaluate Options",
                "4) Final Answer",
            ]
            if any(marker not in stripped for marker in required):
                return False
        # Basic quality floor and truncated-tail guard.
        if words < 80:
            return False
        if stripped.endswith(("\\", "$", "\\$", "(")):
            return False
        return True

    def _build_cache_key() -> str:
        payload = {
            "question_text": body.question_text,
            "options": body.options,
            "correct_answer": body.correct_answer,
            "topic": body.topic,
            "section": body.section,
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    question_doc = None
    if body.question_id:
        try:
            question_doc = await Question.get(PydanticObjectId(body.question_id))
        except Exception:
            question_doc = None

    # Reuse cached solution only if it appears complete.
    if (
        question_doc
        and question_doc.explanation
        and question_doc.explanation != "No explanation available"
        and _is_acceptable_cached_solution(question_doc.explanation)
    ):
        return {"solution": question_doc.explanation, "cached": True}

    # Dedicated cache for PYQ and non-persisted question flows.
    cache_key = _build_cache_key()
    existing_cache = await SolutionCache.find_one(SolutionCache.cache_key == cache_key)
    if existing_cache and _is_acceptable_cached_solution(existing_cache.solution_text):
        # Backfill Question.explanation when possible.
        if question_doc and not _is_acceptable_cached_solution(question_doc.explanation or ""):
            question_doc.explanation = existing_cache.solution_text
            await question_doc.save()
        return {"solution": existing_cache.solution_text, "cached": True}

    if not settings.GEMINI_API_KEY and not settings.GOOGLE_CLOUD_PROJECT:
        raise HTTPException(status_code=503, detail="Gemini service not configured")

    try:
        from google import genai
        from google.genai import types

        if settings.GOOGLE_CLOUD_PROJECT:
            client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION,
            )
        else:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Gemini client unavailable: {e}")

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

Return a COMPLETE, step-by-step teaching solution in this exact structure:

1) Concept Tested
- Name the core concept(s) and formulas/rules needed.

2) Step-by-Step Working
- Show all intermediate steps clearly.
- Do not skip algebra/arithmetic transitions.
- If there are cases/constraints, evaluate each case explicitly.

3) Evaluate Options
- Check all options (A, B, C, D...) briefly and identify why each is right/wrong.

4) Final Answer
- State final option and a one-line reason.

Quality constraints:
- Minimum 6 numbered steps in the "Step-by-Step Working" section.
- Target length: 220-450 words.
- Be concrete and computational, not generic.
- Do NOT return only a short summary sentence.

Use LaTeX for all mathematical expressions (wrap in $...$ for inline, $$...$$ for display).
"""

    structured_prompt = f"""You are an expert tutor. Solve the MCQ fully and return ONLY valid JSON.

{context}Question:
{body.question_text}

Options:
{options_str}

Correct Answer: {correct_text}

Output JSON schema:
{{
  "concept_tested": "string",
  "steps": ["string", "string", "... at least 6 detailed steps ..."],
  "option_analysis": [
    {{"option": "A", "reason": "string"}},
    {{"option": "B", "reason": "string"}}
  ],
  "final_answer": "string"
}}

Rules:
- Return ONLY JSON (no markdown, no prose outside JSON).
- "steps" must have at least 6 clear computational steps.
- Include all options in option_analysis.
- Keep mathematical notation in LaTeX syntax where needed.
"""

    def _is_complete_solution(text: str) -> bool:
        if not text:
            return False
        words = len(text.split())
        has_concept = "1) Concept Tested" in text
        has_steps = "2) Step-by-Step Working" in text
        has_option_eval = "3) Evaluate Options" in text
        has_final = "4) Final Answer" in text

        # Reject clearly truncated tails.
        stripped = text.strip()
        truncated_tail = stripped.endswith(("\\", "$", "\\$", "("))

        return (
            words >= 120
            and has_concept
            and has_steps
            and has_option_eval
            and has_final
            and not truncated_tail
        )

    def _format_structured_solution(payload: dict) -> str:
        concept = str(payload.get("concept_tested", "")).strip()
        steps = payload.get("steps", []) or []
        option_analysis = payload.get("option_analysis", []) or []
        final_answer = str(payload.get("final_answer", "")).strip()

        # Guardrails in case model returns malformed structure
        if not isinstance(steps, list):
            steps = [str(steps)]
        if not isinstance(option_analysis, list):
            option_analysis = [option_analysis]

        lines = []
        lines.append("1) Concept Tested")
        lines.append(concept or "Core concept analysis is required for this question.")
        lines.append("")
        lines.append("2) Step-by-Step Working")
        for i, step in enumerate(steps[:12], start=1):
            lines.append(f"{i}. {str(step).strip()}")
        lines.append("")
        lines.append("3) Evaluate Options")
        for item in option_analysis[:8]:
            if isinstance(item, dict):
                opt = str(item.get("option", "")).strip()
                reason = str(item.get("reason", "")).strip()
                lines.append(f"- {opt}: {reason}")
            else:
                lines.append(f"- {str(item).strip()}")
        lines.append("")
        lines.append("4) Final Answer")
        lines.append(final_answer or correct_text)
        return "\n".join(lines)

    retry_prompt = f"""Solve this MCQ completely in 4 sections exactly:
1) Concept Tested
2) Step-by-Step Working
3) Evaluate Options
4) Final Answer

Question:
{body.question_text}

Options:
{options_str}

Correct Answer: {correct_text}

Rules:
- Minimum 6 detailed working steps.
- Include all options in section 3.
- End your response with this exact token on a new line: END_OF_SOLUTION
"""

    try:
        # First attempt: ask for structured JSON and format it ourselves.
        response = client.models.generate_content(
            model=settings.GEMINI_GENERATION_MODEL,
            contents=structured_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1400,
                response_mime_type="application/json",
            ),
        )

        raw_text = (response.text or "").strip()
        if raw_text:
            try:
                payload = json.loads(raw_text)
                solution_text = _format_structured_solution(payload)
            except Exception:
                solution_text = raw_text
        else:
            solution_text = ""

        # Retry with free-form prompt if structured output is incomplete.
        if not _is_complete_solution(solution_text):
            retry_response = client.models.generate_content(
                model=settings.GEMINI_GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1600,
                ),
            )
            retry_text = (retry_response.text or "").strip()
            if retry_text:
                solution_text = retry_text

        # Final retry: explicit end-marker so we can detect truncation.
        if not _is_complete_solution(solution_text):
            marker_response = client.models.generate_content(
                model=settings.GEMINI_GENERATION_MODEL,
                contents=retry_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1800,
                ),
            )
            marker_text = (marker_response.text or "").strip()
            if "END_OF_SOLUTION" in marker_text:
                marker_text = marker_text.split("END_OF_SOLUTION", 1)[0].rstrip()
            if marker_text:
                solution_text = marker_text

        if not solution_text:
            raise RuntimeError("Empty response from Gemini")

        # Persist solution so future requests can reuse without another LLM call.
        if question_doc and solution_text:
            question_doc.explanation = solution_text
            await question_doc.save()

        # Persist in dedicated solution cache (works for PYQ from YAML as well).
        if solution_text:
            if existing_cache:
                existing_cache.solution_text = solution_text
                existing_cache.provider = "gemini"
                existing_cache.model_name = settings.GEMINI_GENERATION_MODEL
                existing_cache.question_id = body.question_id
                existing_cache.updated_at = datetime.now(timezone.utc)
                await existing_cache.save()
            else:
                await SolutionCache(
                    cache_key=cache_key,
                    solution_text=solution_text,
                    provider="gemini",
                    model_name=settings.GEMINI_GENERATION_MODEL,
                    question_id=body.question_id,
                ).insert()

        return {"solution": solution_text, "cached": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini solution generation failed: {e}")
