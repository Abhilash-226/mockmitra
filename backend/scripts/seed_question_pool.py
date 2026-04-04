"""
seed_question_pool.py — PYQ-Seeded Pool Seeder

Reads PYQ YAML files, builds a lightweight Blueprint with pyq_source tag
for each question, then calls the existing AI generator to produce NEW
original questions inspired by the PYQ. All generated questions are stored
in MongoDB so the QuestionSelector can serve them instantly.

Usage (from backend/ with venv active):
    python -m scripts.seed_question_pool --exam ts_eamcet --target 10
    python -m scripts.seed_question_pool --exam ts_eamcet --target 5 --section Algebra
    python -m scripts.seed_question_pool --exam ts_eamcet --target 3 --topic matrices
    python -m scripts.seed_question_pool --exam ts_eamcet --target 2 --dry-run
    python -m scripts.seed_question_pool --exam ts_eamcet --target 10 --resume
"""

import argparse
import asyncio
import os
import sys
import glob
import random
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml

# ── make sure `backend/` is on sys.path when running as a module ──────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.question import Question, QuestionSource, DifficultyLevel
from app.models.blueprint import Blueprint, DifficultyLevel as BpDifficulty, AnswerType
from app.services.question_generator_v2 import get_question_generator_v2


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _exam_config_path(exam_code: str) -> Path:
    return _BACKEND_DIR / "exam_configs" / f"{exam_code}.yaml"


def _pyq_dir(exam_code: str) -> Path:
    return _BACKEND_DIR / "pyq_papers" / exam_code


def load_exam_structure(exam_code: str) -> List[Dict[str, Any]]:
    """
    Returns a flat list of dicts:
      [{"subject": ..., "section": ..., "topic": ...}, ...]
    """
    cfg_path = _exam_config_path(exam_code)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Exam config not found: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    entries = []
    for subject in cfg.get("subjects", []):
        subj_name = subject["name"]
        for section in subject.get("sections", []):
            sect_name = section["name"]
            for topic in section.get("topics", []):
                entries.append({
                    "subject": subj_name,
                    "section": sect_name,
                    "topic": topic,
                })
    return entries


def load_pyq_questions(exam_code: str) -> List[Dict[str, Any]]:
    """
    Load ALL questions from all PYQ YAML files for an exam.
    Returns list of question dicts enriched with year/shift.
    """
    pyq_dir = _pyq_dir(exam_code)
    if not pyq_dir.exists():
        return []

    all_questions = []
    for fpath in sorted(pyq_dir.glob("*.yaml")):
        with open(fpath, "r", encoding="utf-8") as fh:
            paper = yaml.safe_load(fh)

        year = paper.get("year")
        shift = paper.get("shift")
        for q in paper.get("questions", []):
            q["_year"] = year
            q["_shift"] = shift
            q["_source_file"] = fpath.name
            all_questions.append(q)

    return all_questions


def build_blueprint(pyq_q: Dict[str, Any], subject: str, section: str, topic: str) -> Blueprint:
    """
    Build a lightweight Blueprint from a PYQ question.
    Sets tag=pyq_source so the AI generator treats it as a reference, not a template.
    """
    difficulty_map = {
        "easy": BpDifficulty.EASY,
        "moderate": BpDifficulty.MODERATE,
        "hard": BpDifficulty.HARD,
    }
    raw_diff = str(pyq_q.get("difficulty", "moderate")).lower()
    bp_diff = difficulty_map.get(raw_diff, BpDifficulty.MODERATE)

    # Format options into template text (just for context)
    opts = pyq_q.get("options", {})
    opts_text = ""
    if isinstance(opts, dict):
        opts_text = "  ".join(f"({k}) {v}" for k, v in opts.items())

    template_text = pyq_q.get("text", "")

    return Blueprint(
        id=f"pyq_{pyq_q.get('_source_file', 'unknown')}_{pyq_q.get('id', 'q')}",
        exam=f"TS EAMCET",
        subject=subject,
        section=section,
        topic=topic,
        template=template_text,
        answer_type=AnswerType.CATEGORICAL,
        answer_options=[str(v) for v in opts.values()] if isinstance(opts, dict) and len(opts) >= 2 else ["A", "B", "C", "D"],
        difficulty_level=bp_diff,
        tags=["pyq_source"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# CORE SEEDER
# ─────────────────────────────────────────────────────────────────────────────

async def seed_topic(
    *,
    exam_code: str,
    subject: str,
    section: str,
    topic: str,
    target: int,
    pyq_by_topic: Dict[str, List[Dict]],
    generator,
    dry_run: bool,
    resume: bool,
) -> int:
    """
    Seed `target` AI-generated questions for a single topic.
    Returns the number of questions actually inserted.
    """
    # Count how many already exist
    existing_count = await Question.find({
        "exam_code": exam_code,
        "section": section,
        "topic": topic,
        "source": QuestionSource.AI_GENERATED,
    }).count()

    if resume and existing_count >= target:
        print(f"  ✅ {section}/{topic}: already has {existing_count} (target={target}), skipping.")
        return 0

    needed = target - existing_count if resume else target
    if needed <= 0:
        return 0

    # Get PYQ questions for context (match by section or topic)
    references = pyq_by_topic.get(topic, [])
    if not references:
        references = pyq_by_topic.get(section, [])
    if not references:
        # Fall back to any questions for this subject
        references = [q for pool in pyq_by_topic.values() for q in pool]

    if not references:
        print(f"  ⚠️  {section}/{topic}: No PYQ references found — skipping.")
        return 0

    print(f"  🔄 {section}/{topic}: generating {needed} questions (existing={existing_count}, target={target})")

    inserted = 0

    # Collect existing texts for deduplication
    existing_texts: List[str] = []
    if not dry_run:
        existing_qs = await Question.find({
            "exam_code": exam_code,
            "section": section,
            "topic": topic,
        }).to_list()
        existing_texts = [q.question_text for q in existing_qs]

    for i in range(needed):
        ref = random.choice(references)
        bp = build_blueprint(ref, subject, section, topic)

        if dry_run:
            print(f"    [DRY-RUN] Would generate from PYQ: {ref.get('text', '')[:80]}...")
            inserted += 1
            continue

        try:
            gen_q = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda _bp=bp: generator.generate_from_blueprint(_bp, use_ai_phrasing=False),
            )
        except Exception as e:
            print(f"    ❌ Generator error: {e}")
            continue

        if not gen_q:
            print(f"    ⚠️  Generation returned None for {topic} (attempt {i+1})")
            continue

        # Validate
        if gen_q.correct_option_index < 0 or gen_q.correct_option_index >= len(gen_q.options):
            print(f"    ⚠️  Invalid correct_option_index, skipping.")
            continue

        # Deduplication (difflib similarity)
        from difflib import SequenceMatcher
        new_text = gen_q.question_text
        is_dup = any(
            SequenceMatcher(None, new_text.lower(), ex.lower()).ratio() >= 0.82
            for ex in existing_texts
        )
        if is_dup:
            print(f"    ⚠️  Duplicate detected, skipping.")
            continue

        # Map difficulty
        diff_map = {"easy": "easy", "moderate": "medium", "hard": "hard"}
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
        existing_texts.append(new_text)
        inserted += 1
        print(f"    ✅ [{inserted}/{needed}] Saved: {gen_q.question_text[:70]}...")

    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Seed the MockMitra question pool with PYQ-inspired AI questions."
    )
    parser.add_argument("--exam", default="ts_eamcet", help="Exam code (default: ts_eamcet)")
    parser.add_argument("--target", type=int, default=5, help="Questions to generate per topic (default: 5)")
    parser.add_argument("--section", default=None, help="Only seed this section (e.g. Algebra)")
    parser.add_argument("--topic", default=None, help="Only seed this topic (e.g. matrices)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing to DB")
    parser.add_argument("--resume", action="store_true", help="Skip topics already at target")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  MockMitra Seeder — {args.exam.upper()}")
    print(f"  Target: {args.target} per topic | Section: {args.section or 'ALL'} | Topic: {args.topic or 'ALL'}")
    print(f"  Mode: {'DRY-RUN (no DB writes)' if args.dry_run else 'LIVE'} | Resume: {args.resume}")
    print(f"{'='*60}\n")

    # ── DB setup ──────────────────────────────────────────────────────────────
    if not args.dry_run:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        await init_beanie(
            database=client[settings.MONGODB_DB_NAME],
            document_models=[Question],
        )
        print("✅ Connected to MongoDB.\n")

    # ── Load exam structure ───────────────────────────────────────────────────
    entries = load_exam_structure(args.exam)

    # Filter by section / topic if specified
    if args.section:
        entries = [e for e in entries if e["section"].lower() == args.section.lower()]
    if args.topic:
        entries = [e for e in entries if e["topic"].lower() == args.topic.lower()]

    if not entries:
        print("❌ No matching topics found. Check --section / --topic values.")
        return

    # ── Load PYQ data ─────────────────────────────────────────────────────────
    print(f"Loading PYQ papers for {args.exam}...")
    all_pyqs = load_pyq_questions(args.exam)
    print(f"  Loaded {len(all_pyqs)} PYQ questions from YAML files.\n")

    # Index by topic for fast lookup
    pyq_by_topic: Dict[str, List[Dict]] = {}
    for q in all_pyqs:
        t = q.get("topic", "")
        s = q.get("section", "")
        for key in (t, s):
            if key:
                pyq_by_topic.setdefault(key, []).append(q)

    # ── Generator ─────────────────────────────────────────────────────────────
    generator = get_question_generator_v2()

    # ── Seed each topic ───────────────────────────────────────────────────────
    total_inserted = 0
    for entry in entries:
        count = await seed_topic(
            exam_code=args.exam,
            subject=entry["subject"],
            section=entry["section"],
            topic=entry["topic"],
            target=args.target,
            pyq_by_topic=pyq_by_topic,
            generator=generator,
            dry_run=args.dry_run,
            resume=args.resume,
        )
        total_inserted += count

    print(f"\n{'='*60}")
    print(f"  Seeding complete. {'(DRY-RUN — nothing written)' if args.dry_run else f'Total inserted: {total_inserted}'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
