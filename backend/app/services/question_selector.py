"""
question_selector.py — Unseen-First Question Selector Service

Core logic:
1. Fetch all question IDs the user has already seen (from TestResponse records)
2. Query the DB pool for UNSEEN questions matching the criteria
3. If pool covers >= MIN_COVERAGE of the requested count, serve from DB instantly
4. Otherwise, call AI fallback to generate the deficit, deduplicate, save, and return

This replaces the ad-hoc inline pool query + parallel AI worker block in tests.py.
"""

import random
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any

from beanie import PydanticObjectId

from app.models.question import Question, QuestionSource, DifficultyLevel
from app.models.test import TestAttempt, TestResponse as TestResponseModel
from app.models.blueprint import Blueprint, DifficultyLevel as BpDifficulty, AnswerType


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MIN_COVERAGE = 0.8           # Trigger AI if DB covers < 80% of requested count
DEDUP_THRESHOLD = 0.82       # SequenceMatcher ratio above which two questions are "duplicate"


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

class QuestionSelector:
    """
    Selects questions for a test attempt using unseen-first logic.

    Always tries the DB first. Falls back to AI only when the pool
    is insufficient. New AI-generated questions are saved to the pool
    so future users benefit automatically.
    """

    def __init__(self):
        # Import lazily to avoid circular imports (services importing models, etc.)
        from app.services.question_generator_v2 import get_question_generator_v2
        self._generator = get_question_generator_v2()

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    async def select_questions(
        self,
        *,
        user_id: str,
        exam_code: str,
        section: str,
        topic: Optional[str],
        difficulty: Optional[str],
        count: int,
        topics: Optional[List[str]] = None,
    ) -> List[Question]:
        """
        Return `count` questions for the given criteria.

        Args:
            user_id:    User's ObjectId string (for seen-question tracking).
            exam_code:  e.g. "ts_eamcet"
            section:    e.g. "Algebra"
            topic:      Single topic string, or None to allow any topic in section.
            difficulty: "easy" | "medium" | "hard" | None (any)
            count:      Number of questions needed.
            topics:     Optional list of topics (union — used for topic-wise tests).

        Returns:
            List of Question documents of length <= count.
        """
        # 1. Get seen question IDs for this user
        seen_ids = await self._get_user_seen_ids(user_id)

        # 2. Fetch unseen from pool
        pool = await self._fetch_unseen(
            exam_code=exam_code,
            section=section,
            topic=topic,
            topics=topics,
            difficulty=difficulty,
            seen_ids=seen_ids,
            limit=count * 3,  # fetch extra for variety
        )

        # 3. Sample from pool up to count
        if len(pool) >= count:
            return random.sample(pool, count)   # ⚡ instant DB serve

        # 4. AI fallback for the deficit
        needed = count - len(pool)
        existing_texts = [q.question_text for q in pool]
        ai_questions = await self._generate_and_store(
            exam_code=exam_code,
            section=section,
            topic=topic or (topics[0] if topics else None),
            difficulty=difficulty,
            count=needed,
            existing_texts=existing_texts,
        )

        return pool + ai_questions

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_user_seen_ids(self, user_id: str) -> List[PydanticObjectId]:
        """
        Collect all question_ids the user has ever seen (across all attempts).
        We go through TestAttempt → TestResponse.
        """
        try:
            user_oid = PydanticObjectId(user_id)
        except Exception:
            return []

        # All attempt IDs for this user
        attempts = await TestAttempt.find(
            TestAttempt.user_id == user_oid
        ).to_list()

        if not attempts:
            return []

        attempt_ids = [a.id for a in attempts]

        # All responses across those attempts
        responses = await TestResponseModel.find(
            {"attempt_id": {"$in": attempt_ids}}
        ).to_list()

        return [r.question_id for r in responses]

    async def _fetch_unseen(
        self,
        *,
        exam_code: str,
        section: str,
        topic: Optional[str],
        topics: Optional[List[str]],
        difficulty: Optional[str],
        seen_ids: List[PydanticObjectId],
        limit: int,
    ) -> List[Question]:
        """
        Query the DB for questions the user hasn't seen yet.
        Uses compound index: (exam_code, section, topic, difficulty).
        """
        query: Dict[str, Any] = {
            "exam_code": exam_code,
            "section": section,
        }

        # Topic filter
        if topic:
            query["topic"] = topic
        elif topics:
            query["topic"] = {"$in": topics}

        # Difficulty filter
        if difficulty and difficulty != "mixed":
            # Map "medium" → "medium" (DB uses medium, not moderate)
            diff_map = {"easy": "easy", "medium": "medium", "hard": "hard",
                        "moderate": "medium"}
            mapped = diff_map.get(difficulty.lower(), difficulty.lower())
            try:
                query["difficulty"] = DifficultyLevel(mapped).value
            except ValueError:
                pass  # ignore invalid difficulty, fetch all

        # Exclude seen questions
        if seen_ids:
            query["_id"] = {"$nin": seen_ids}

        return await Question.find(query).limit(limit).to_list()

    async def _generate_and_store(
        self,
        *,
        exam_code: str,
        section: str,
        topic: Optional[str],
        difficulty: Optional[str],
        count: int,
        existing_texts: List[str],
    ) -> List[Question]:
        """
        Use AI to generate `count` new questions, deduplicate, and persist them.
        Returns the saved Question documents.
        """
        import asyncio

        # Build a lightweight pyq_source Blueprint
        bp = self._build_fallback_blueprint(exam_code, section, topic, difficulty)

        new_questions: List[Question] = []
        texts_so_far = list(existing_texts)
        max_attempts = count * 4  # cap retries

        loop = asyncio.get_event_loop()

        for _ in range(max_attempts):
            if len(new_questions) >= count:
                break

            try:
                gen_q = await loop.run_in_executor(
                    None,
                    lambda _bp=bp: self._generator.generate_from_blueprint(_bp, use_ai_phrasing=False),
                )
            except Exception as e:
                print(f"QuestionSelector AI error: {e}")
                continue

            if not gen_q:
                continue

            if gen_q.correct_option_index < 0 or gen_q.correct_option_index >= len(gen_q.options):
                continue

            # Deduplication
            if self._is_duplicate(gen_q.question_text, texts_so_far):
                continue

            # Map difficulty
            diff_map = {"easy": "easy", "moderate": "medium", "hard": "hard",
                        "medium": "medium"}
            q_diff_str = diff_map.get(str(gen_q.difficulty_level).lower(), "medium")
            try:
                q_diff = DifficultyLevel(q_diff_str)
            except ValueError:
                q_diff = DifficultyLevel.MEDIUM

            db_q = Question(
                question_text=gen_q.question_text,
                options={
                    "a": gen_q.options[0],
                    "b": gen_q.options[1],
                    "c": gen_q.options[2],
                    "d": gen_q.options[3],
                },
                correct_option=["a", "b", "c", "d"][gen_q.correct_option_index],
                explanation=gen_q.solution,
                exam_code=exam_code,
                section=section,
                topic=topic,
                difficulty=q_diff,
                source=QuestionSource.AI_GENERATED,
            )

            await db_q.insert()
            texts_so_far.append(gen_q.question_text)
            new_questions.append(db_q)
            print(f"QuestionSelector: generated & saved '{gen_q.question_text[:60]}...'")

        return new_questions

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────────────────

    def _is_duplicate(self, new_text: str, existing_texts: List[str]) -> bool:
        """True if new_text is too similar to any existing question."""
        for ex in existing_texts:
            ratio = SequenceMatcher(None, new_text.lower(), ex.lower()).ratio()
            if ratio >= DEDUP_THRESHOLD:
                return True
        return False

    def _build_fallback_blueprint(
        self,
        exam_code: str,
        section: str,
        topic: Optional[str],
        difficulty: Optional[str],
    ) -> Blueprint:
        """Build a minimal blueprint for AI fallback generation."""
        diff_map = {
            "easy": BpDifficulty.EASY,
            "medium": BpDifficulty.MODERATE,
            "hard": BpDifficulty.HARD,
            "moderate": BpDifficulty.MODERATE,
        }
        bp_diff = diff_map.get((difficulty or "moderate").lower(), BpDifficulty.MODERATE)

        # Infer subject from section/exam (simple heuristic)
        subject = _section_to_subject(section)

        template = (
            f"Generate a challenging {section} question"
            + (f" on the topic of {topic.replace('_', ' ')}" if topic else "")
            + " for TS EAMCET."
        )

        return Blueprint(
            id=f"fallback_{exam_code}_{section}_{topic or 'general'}",
            exam="TS EAMCET",
            subject=subject,
            section=section,
            topic=topic,
            template=template,
            answer_type=AnswerType.CATEGORICAL,
            answer_options=["A", "B", "C", "D"],
            difficulty_level=bp_diff,
            tags=["ai_fallback"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON & FACTORY
# ─────────────────────────────────────────────────────────────────────────────

_selector_instance: Optional[QuestionSelector] = None


def get_question_selector() -> QuestionSelector:
    """Return (or create) the module-level QuestionSelector singleton."""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = QuestionSelector()
    return _selector_instance


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────

_SECTION_SUBJECT_MAP = {
    # Mathematics sections
    "algebra": "Mathematics",
    "trigonometry": "Mathematics",
    "vector algebra": "Mathematics",
    "coordinate geometry": "Mathematics",
    "calculus": "Mathematics",
    "probability & statistics": "Mathematics",
    "probability and statistics": "Mathematics",
    # Physics sections
    "mechanics": "Physics",
    "thermal physics": "Physics",
    "oscillations and waves": "Physics",
    "electricity and magnetism": "Physics",
    "optics": "Physics",
    "modern physics": "Physics",
    "communication systems": "Physics",
    # Chemistry sections
    "physical chemistry": "Chemistry",
    "inorganic chemistry": "Chemistry",
    "organic chemistry": "Chemistry",
}


def _section_to_subject(section: str) -> str:
    return _SECTION_SUBJECT_MAP.get(section.lower(), "Mathematics")
