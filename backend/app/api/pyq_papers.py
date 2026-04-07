"""
PYQ Papers API - Previous Year Question Papers

Provides endpoints for:
- Listing available papers by exam
- Getting paper details and questions
- Starting a paper attempt
- Submitting a PYQ attempt (persists to DB for history + analytics)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from beanie import PydanticObjectId
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import asyncio
import time
import yaml
import os
import re
import unicodedata

from app.core.security import get_current_user
from app.models.question import Question, QuestionSource, DifficultyLevel
from app.models.test import Test, TestAttempt, TestStatus, TestType, TestResponse as TestResponseModel
from app.models.pyq_solution import PyQSolution

router = APIRouter()

# Path to PYQ papers directory (organized by exam)
PYQ_PAPERS_DIR = Path(__file__).parent.parent.parent / "pyq_papers"

# Exam codes to folder names mapping
EXAM_FOLDERS = {
    "ts_eamcet": "ts_eamcet",
    # Future: "jee_main": "jee_main", "neet": "neet"
}


def _normalize_latex_text(value: Any) -> str:
    """Normalize OCR/YAML LaTeX text so frontend receives consistent math strings."""
    if value is None:
        return ""

    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    # Remove combining marks and zero-width chars that can corrupt commands like \frac
    text = re.sub(r"[\u0300-\u036f\u200B-\u200D\uFEFF]", "", text)
    # Convert escaped dollar delimiters (\$ or \\$) to plain $.
    text = re.sub(r"\\+\$", "$", text)
    # Collapse repeated backslashes before command names, e.g. \\frac -> \frac
    text = re.sub(r"\\{2,}(?=[A-Za-z])", r"\\", text)

    return text


def _normalize_option_value(value: Any) -> Any:
    """Normalize option payload while preserving structured image options."""
    if isinstance(value, dict):
        normalized: Dict[str, Any] = {}
        for key, item in value.items():
            # Preserve raw image paths so frontend can build absolute URLs.
            if key == "image" and isinstance(item, str):
                normalized[key] = item
            else:
                normalized[key] = _normalize_option_value(item)
        return normalized

    if isinstance(value, list):
        return [_normalize_option_value(item) for item in value]

    return _normalize_latex_text(value)


def get_exam_yaml_dir(exam_code: str) -> Path:
    """Get the YAML directory for an exam."""
    folder = EXAM_FOLDERS.get(exam_code, exam_code)
    return PYQ_PAPERS_DIR / folder


def get_exam_pdf_dir(exam_code: str) -> Path:
    """Get the PDF directory for an exam."""
    folder = EXAM_FOLDERS.get(exam_code, exam_code)
    return Path(__file__).parent.parent.parent.parent / "PYQS" / "exams" / folder / "pdfs"


class PaperSection(BaseModel):
    """Section within a paper"""
    code: str
    name: str
    question_count: int


class PaperMetadata(BaseModel):
    """Paper metadata"""
    total_questions: int = 160
    duration_minutes: int = 180
    total_marks: int = 160
    negative_marking: bool = False
    cutoff_general: Optional[int] = None


class PaperQuestion(BaseModel):
    """Question in a paper"""
    number: int
    section: str
    text: str
    options: Dict[str, Any]
    correct_answer: str
    image: Optional[str] = None
    topic: Optional[str] = None
    subject: Optional[str] = None


class PaperSummary(BaseModel):
    """Summary of a paper for listing"""
    id: str  # e.g., "ts_eamcet_2024_1"
    exam: str
    year: int
    shift: int
    date: Optional[str] = None
    session: Optional[str] = None
    total_questions: int
    duration_minutes: int
    is_extracted: bool = False  # Whether questions are available


class PaperDetail(BaseModel):
    """Full paper with questions"""
    id: str
    exam: str
    year: int
    shift: int
    date: Optional[str] = None
    session: Optional[str] = None
    source_pdf: Optional[str] = None
    metadata: PaperMetadata
    sections: List[PaperSection]
    questions: List[PaperQuestion]


class PapersListResponse(BaseModel):
    """Response containing list of papers"""
    exam: str
    total_papers: int
    extracted_papers: int
    papers: List[PaperSummary]


def parse_pdf_filename(filename: str) -> Dict[str, Any]:
    """
    Parse PDF filename to extract year and shift.
    Examples:
        2024.pdf -> year=2024, shift=1
        2024-1.pdf -> year=2024, shift=1
        2024-2.pdf -> year=2024, shift=2
    """
    name = filename.replace('.pdf', '')
    
    if '-' in name:
        parts = name.split('-')
        year = int(parts[0])
        shift = int(parts[1])
    else:
        year = int(name)
        shift = 1
    
    return {"year": year, "shift": shift}


def load_paper_yaml(paper_id: str, exam_code: str = "ts_eamcet") -> Optional[Dict[str, Any]]:
    """Load paper YAML file if it exists"""
    yaml_dir = get_exam_yaml_dir(exam_code)
    yaml_path = yaml_dir / f"{paper_id}.yaml"
    if yaml_path.exists():
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


# In-memory cache for available papers
_papers_cache: Dict[str, Any] = {}  # {exam_code: {"data": [...], "timestamp": float}}
_PAPERS_CACHE_TTL = 300  # 5 minutes


def get_available_papers(exam_code: str = "ts_eamcet") -> List[Dict[str, Any]]:
    """
    Get all available papers for an exam (both extracted and pending).
    Results are cached for 5 minutes to avoid repeated filesystem scanning.
    
    Args:
        exam_code: Exam code (e.g., "ts_eamcet")
    
    Returns:
        List of paper info dicts
    """
    # Check cache first
    cached = _papers_cache.get(exam_code)
    if cached and (time.monotonic() - cached["timestamp"]) < _PAPERS_CACHE_TTL:
        return cached["data"]

    pyq_pdf_dir = get_exam_pdf_dir(exam_code)
    pyq_yaml_dir = get_exam_yaml_dir(exam_code)
    
    papers = []
    seen_ids = set()
    
    exam_name = exam_code.upper().replace("_", " ")  # ts_eamcet -> TS EAMCET
    
    # First, scan extracted YAML files.
    # NOTE: Keep this path lightweight for production by avoiding full YAML parsing
    # for every paper in list views. Detailed parsing is done only in get_paper().
    if pyq_yaml_dir.exists():
        for yaml_file in sorted(pyq_yaml_dir.glob(f"{exam_code}_*.yaml")):
            paper_id = yaml_file.stem  # e.g., ts_eamcet_2020_1
            if paper_id in seen_ids:
                continue

            parts = paper_id.split("_")
            year = int(parts[2]) if len(parts) >= 4 and parts[2].isdigit() else 0
            shift = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 1

            papers.append({
                "id": paper_id,
                "exam": exam_name,
                "year": year,
                "shift": shift,
                "source_pdf": None,
                "is_extracted": True,
                "date": None,
                "session": None,
                "total_questions": 160,
                "duration_minutes": 180,
            })
            seen_ids.add(paper_id)
    
    # Then, scan PDF files for any that don't have YAML yet
    if pyq_pdf_dir.exists():
        for pdf_file in sorted(pyq_pdf_dir.glob("*.pdf")):
            info = parse_pdf_filename(pdf_file.name)
            paper_id = f"{exam_code}_{info['year']}_{info['shift']}"
            
            if paper_id in seen_ids:
                continue
            
            # Check if extracted YAML exists
            is_extracted = (pyq_yaml_dir / f"{paper_id}.yaml").exists()
            
            papers.append({
                "id": paper_id,
                "exam": exam_name,
                "year": info["year"],
                "shift": info["shift"],
                "source_pdf": pdf_file.name,
                "is_extracted": is_extracted,
                "date": None,
                "session": None,
                "total_questions": 160,
                "duration_minutes": 180,
            })
            seen_ids.add(paper_id)
    
    # Sort by year desc, then shift
    papers.sort(key=lambda x: (-x["year"], x["shift"]))
    
    # Store in cache
    _papers_cache[exam_code] = {"data": papers, "timestamp": time.monotonic()}
    
    return papers


@router.get("/papers", response_model=PapersListResponse)
async def list_papers(exam: str = "ts_eamcet", exam_code: Optional[str] = None):
    """
    List all available PYQ papers for an exam.
    
    Scans the PYQS folder for PDFs and checks which ones have been extracted.
    """
    effective_exam = (exam_code or exam)
    normalized_exam_code = effective_exam.lower().replace("-", "_").replace(" ", "_")
    papers = await asyncio.to_thread(get_available_papers, normalized_exam_code)
    
    extracted_count = sum(1 for p in papers if p["is_extracted"])
    
    return PapersListResponse(
        exam=normalized_exam_code.upper(),
        total_papers=len(papers),
        extracted_papers=extracted_count,
        papers=[PaperSummary(**p) for p in papers]
    )


@router.get("/papers/{paper_id}", response_model=PaperDetail)
async def get_paper(paper_id: str):
    """
    Get full paper details including questions.
    
    If the paper has not been extracted yet, returns empty questions list.
    """
    # Extract exam code from paper_id (e.g., ts_eamcet_2020_1 -> ts_eamcet)
    parts = paper_id.split("_")
    if len(parts) >= 4:
        exam_code = f"{parts[0]}_{parts[1]}"
        year = int(parts[2])
        shift = int(parts[3])
    else:
        raise HTTPException(status_code=400, detail="Invalid paper ID format")
    
    yaml_data = load_paper_yaml(paper_id, exam_code)
    
    if not yaml_data:
        # Paper not extracted yet - return skeleton based on PDF info
        return PaperDetail(
            id=paper_id,
            exam="TS_EAMCET",
            year=year,
            shift=shift,
            metadata=PaperMetadata(),
            sections=[
                PaperSection(code="MAT", name="Mathematics", question_count=80),
                PaperSection(code="PHY", name="Physics", question_count=40),
                PaperSection(code="CHE", name="Chemistry", question_count=40),
            ],
            questions=[]
        )
    
    # Parse questions
    questions = []
    for q in yaml_data.get("questions", []):
        normalized_options = {
            str(k): _normalize_option_value(v)
            for k, v in (q.get("options", {}) or {}).items()
        }
        questions.append(PaperQuestion(
            number=q.get("number") or q.get("id", 0),
            section=q.get("section", ""),
            text=_normalize_latex_text(q.get("text", "")),
            options=normalized_options,
            correct_answer=q.get("correct_answer") or q.get("correct", ""),
            image=q.get("image"),
            topic=q.get("topic"),
            subject=q.get("subject"),
        ))
    
    # Parse sections
    sections = []
    for s in yaml_data.get("sections", []):
        sections.append(PaperSection(
            code=s.get("code", ""),
            name=s.get("name", ""),
            question_count=s.get("question_count", 0),
        ))
    
    return PaperDetail(
        id=paper_id,
        exam=yaml_data.get("exam", "TS_EAMCET"),
        year=yaml_data.get("year", 0),
        shift=yaml_data.get("shift", 1),
        date=yaml_data.get("date"),
        session=yaml_data.get("session"),
        source_pdf=yaml_data.get("source_pdf"),
        metadata=PaperMetadata(**yaml_data.get("metadata", {})),
        sections=sections,
        questions=questions,
    )


@router.get("/papers/{paper_id}/questions")
async def get_paper_questions(paper_id: str, section: Optional[str] = None):
    """
    Get questions for a paper, optionally filtered by section.
    
    Returns questions in exam-ready format (without correct answers visible).
    """
    paper = await get_paper(paper_id)
    
    if not paper.questions:
        raise HTTPException(
            status_code=404, 
            detail="Paper not yet extracted. Please run the extraction script first."
        )
    
    questions = paper.questions
    
    if section:
        questions = [q for q in questions if q.section.upper() == section.upper()]
    
    # Return without correct answer for exam mode
    return {
        "paper_id": paper_id,
        "total_questions": len(questions),
        "questions": [
            {
                "number": q.number,
                "section": q.section,
                "text": _normalize_latex_text(q.text),
                "options": {
                    str(k): _normalize_option_value(v)
                    for k, v in (q.options or {}).items()
                },
                "image": q.image,
                "topic": q.topic,
                "subject": q.subject,
                # "correct_answer" is intentionally omitted for exam mode
            }
            for q in questions
        ]
    }


@router.get("/years")
async def get_available_years(exam: str = "ts_eamcet", exam_code: Optional[str] = None):
    """
    Get list of years with available papers.
    """
    effective_exam = (exam_code or exam)
    normalized_exam_code = effective_exam.lower().replace("-", "_").replace(" ", "_")
    papers = await asyncio.to_thread(get_available_papers, normalized_exam_code)
    
    # Group by year
    years_data = {}
    for p in papers:
        year = p["year"]
        if year not in years_data:
            years_data[year] = {
                "year": year,
                "total_shifts": 0,
                "extracted_shifts": 0,
                "shifts": []
            }
        
        years_data[year]["total_shifts"] += 1
        if p["is_extracted"]:
            years_data[year]["extracted_shifts"] += 1
        years_data[year]["shifts"].append({
            "shift": p["shift"],
            "is_extracted": p["is_extracted"],
            "paper_id": p["id"]
        })
    
    # Sort shifts within each year
    for year_data in years_data.values():
        year_data["shifts"].sort(key=lambda x: x["shift"])
    
    # Return sorted by year descending
    return {
        "exam": normalized_exam_code.upper(),
        "years": sorted(years_data.values(), key=lambda x: -x["year"])
    }


# ── PYQ Submission ───────────────────────────────────────────────────────────

class PYQAnswer(BaseModel):
    question_number: int
    selected_option: Optional[str] = None   # "A", "B", "C", "D" or null
    time_spent_seconds: int = 0

class PYQSubmitRequest(BaseModel):
    paper_id: str
    answers: List[PYQAnswer]
    time_taken_seconds: int = 0


@router.get("/solutions/{paper_id}/{question_number}")
async def get_pyq_solution(
    paper_id: str,
    question_number: int,
    user_id: str = Depends(get_current_user),
):
    """Fetch pre-generated solution for a PYQ question by paper/question identifiers."""
    _ = user_id
    solution_doc = await PyQSolution.find_one(
        PyQSolution.paper_id == paper_id,
        PyQSolution.question_number == question_number,
    )

    if not solution_doc:
        raise HTTPException(
            status_code=404,
            detail="Solution not available yet. Please try again after bulk generation completes.",
        )

    return {
        "paper_id": solution_doc.paper_id,
        "question_number": solution_doc.question_number,
        "solution": solution_doc.solution_text,
        "provider": solution_doc.provider,
        "model": solution_doc.model_name,
        "generated_at": solution_doc.updated_at,
    }


@router.post("/submit")
async def submit_pyq_test(
    body: PYQSubmitRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Submit a PYQ test attempt.  Persists questions into the questions collection,
    creates Test + TestAttempt + TestResponse records so the attempt appears in
    test-history and supports the same detailed-analytics page as mock tests.
    """
    # 1. Parse paper_id → exam_code, year, shift
    parts = body.paper_id.split("_")
    if len(parts) < 4:
        raise HTTPException(status_code=400, detail="Invalid paper_id format")
    exam_code = f"{parts[0]}_{parts[1]}"
    year = int(parts[2])
    shift = int(parts[3])

    # 2. Load YAML to get correct answers and full question data
    yaml_data = load_paper_yaml(body.paper_id, exam_code)
    if not yaml_data or not yaml_data.get("questions"):
        raise HTTPException(status_code=404, detail="Paper not found or has no questions")

    yaml_questions = yaml_data["questions"]
    metadata = yaml_data.get("metadata", {})

    # Build a lookup: question_number → yaml_question
    q_by_number: Dict[int, dict] = {}
    for q in yaml_questions:
        raw_num = q.get("number") or q.get("id", 0)
        try:
            num = int(raw_num)
        except (TypeError, ValueError):
            # Skip malformed rows so one bad YAML item does not break submission.
            continue
        q_by_number[num] = q

    # 3. Insert / reuse Question documents in DB (bulk mode for performance)
    #    On production this endpoint can timeout if we do 160+ find_one calls.
    #    Instead: fetch all PYQ questions for (exam_code, year) once, then insert only missing.
    existing_questions = await Question.find(
        Question.exam_code == exam_code,
        Question.source == QuestionSource.PYQ,
        Question.source_paper_id == body.paper_id,
    ).to_list()
    existing_by_number: Dict[int, Question] = {
        int(q.source_question_number): q
        for q in existing_questions
        if q.source_question_number is not None
    }

    question_docs: Dict[int, Question] = {}  # number -> Question doc
    docs_to_insert: list[Question] = []
    nums_to_insert: list[int] = []

    for num, yq in q_by_number.items():
        existing = existing_by_number.get(num)
        if existing:
            if (
                existing.source_paper_id != body.paper_id
                or existing.source_question_number != num
            ):
                existing.source_paper_id = body.paper_id
                existing.source_question_number = num
                await existing.save()
            question_docs[num] = existing
            continue

        q_text = str(yq.get("text", ""))

        opts_raw = yq.get("options", {}) or {}
        options_map: Dict[str, Any] = {
            str(k).lower(): v for k, v in opts_raw.items()
        }
        correct_raw = str(yq.get("correct_answer") or yq.get("correct", "")).strip().lower()

        docs_to_insert.append(
            Question(
                question_text=q_text,
                options=options_map,
                correct_option=correct_raw,
                image=yq.get("image"),
                explanation=yq.get("explanation"),
                exam_code=exam_code,
                section=yq.get("subject") or yq.get("section"),
                topic=yq.get("topic"),
                difficulty=DifficultyLevel.MEDIUM,
                source=QuestionSource.PYQ,
                year=year,
                source_paper_id=body.paper_id,
                source_question_number=num,
            )
        )
        nums_to_insert.append(num)

    if docs_to_insert:
        await Question.insert_many(docs_to_insert)

        # Reload newly inserted records to guarantee IDs are present for response links.
        inserted_questions = await Question.find(
            Question.exam_code == exam_code,
            Question.source == QuestionSource.PYQ,
            Question.source_paper_id == body.paper_id,
            {"source_question_number": {"$in": nums_to_insert}},
        ).to_list()
        inserted_by_number: Dict[int, Question] = {
            int(q.source_question_number): q
            for q in inserted_questions
            if q.source_question_number is not None
        }
        for num in nums_to_insert:
            q_doc = inserted_by_number.get(num)
            if q_doc:
                question_docs[num] = q_doc

    question_ids = [doc.id for doc in question_docs.values()]

    # 4. Create a Test document (template)
    exam_label = exam_code.upper().replace("_", " ")
    test = Test(
        title=f"PYQ {exam_label} {year} Shift-{shift}",
        exam_code=exam_code,
        test_type=TestType.FULL_LENGTH,
        total_questions=len(question_ids),
        total_marks=float(len(question_ids)),
        duration_minutes=metadata.get("duration_minutes", 180),
        negative_marking=0.0,
        question_ids=question_ids,
    )
    await test.insert()

    # 5. Create TestAttempt
    now = datetime.now(timezone.utc)
    attempt = TestAttempt(
        user_id=PydanticObjectId(user_id),
        test_id=test.id,
        status=TestStatus.COMPLETED,
        started_at=now,
        completed_at=now,
        time_taken_seconds=body.time_taken_seconds,
    )

    # 6. Score answers & build TestResponse records
    correct = 0
    wrong = 0
    skipped = 0
    responses_to_insert: list[TestResponseModel] = []

    for ans in body.answers:
        q_doc = question_docs.get(ans.question_number)
        if not q_doc:
            continue

        # Normalise user's selected option to lowercase
        selected = ans.selected_option.lower() if ans.selected_option else None

        is_correct = None
        if selected is None:
            skipped += 1
        elif selected == q_doc.correct_option:
            correct += 1
            is_correct = True
        else:
            wrong += 1
            is_correct = False

        responses_to_insert.append(
            TestResponseModel(
                attempt_id=PydanticObjectId("000000000000000000000000"),  # placeholder, updated below
                question_id=q_doc.id,
                selected_option=selected,
                is_correct=is_correct,
                time_spent_seconds=ans.time_spent_seconds,
                answered_at=now,
            )
        )

    attempt.total_attempted = correct + wrong
    attempt.correct_answers = correct
    attempt.wrong_answers = wrong
    attempt.skipped = skipped
    attempt.score = float(correct)
    attempt.percentage = round((correct / len(question_ids) * 100), 2) if question_ids else 0.0
    await attempt.insert()

    # Patch the placeholder attempt_id in responses, then bulk-insert
    for r in responses_to_insert:
        r.attempt_id = attempt.id
    if responses_to_insert:
        await TestResponseModel.insert_many(responses_to_insert)

    return {
        "attempt_id": str(attempt.id),
        "score": attempt.score,
        "percentage": attempt.percentage,
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "total": len(question_ids),
    }
