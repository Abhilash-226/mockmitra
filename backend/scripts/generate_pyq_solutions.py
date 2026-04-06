import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from app.core.config import settings
from app.core.database import close_db, init_db
from app.models.pyq_solution import PyQSolution


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk-generate and persist PYQ solutions from YAML papers."
    )
    parser.add_argument(
        "--exam",
        default="ts_eamcet",
        help="Exam folder under backend/pyq_papers (default: ts_eamcet)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N questions (0 means all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if a stored solution already exists",
    )
    parser.add_argument(
        "--paper-id",
        default=None,
        help="Only process a specific paper id, e.g. ts_eamcet_2024_1",
    )
    return parser.parse_args()


def _question_hash(question_text: str, options: Dict[str, Any], correct_answer: str) -> str:
    payload = {
        "question_text": question_text,
        "options": options,
        "correct_answer": correct_answer,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _options_to_lines(options: Dict[str, Any]) -> str:
    lines = []
    labels = ["A", "B", "C", "D", "E", "F"]

    for idx, key in enumerate(sorted(options.keys())):
        label = labels[idx] if idx < len(labels) else str(idx + 1)
        value = options[key]
        if isinstance(value, dict) and isinstance(value.get("image"), str):
            text_value = f"[image option: {value['image']}]"
        else:
            text_value = str(value)
        lines.append(f"{label}. {text_value}")

    return "\n".join(lines)


def _build_prompt(question_text: str, options: Dict[str, Any], correct_answer: str, section: Optional[str], topic: Optional[str]) -> str:
    context = ""
    if section or topic:
        context = f"Section: {section or ''}\\nTopic: {topic or ''}\\n"

    return f"""You are an expert tutor helping students solve Indian competitive exam MCQs.

{context}Question:
{question_text}

Options:
{_options_to_lines(options)}

Correct Answer: {correct_answer}

Return a complete, step-by-step solution in this exact format:

1) Concept Tested
- Mention formulas/rules used.

2) Step-by-Step Working
- Show all intermediate steps.
- Include all needed algebra/arithmetic transitions.

3) Evaluate Options
- Briefly validate all options and why they are right/wrong.

4) Final Answer
- State the final option and one-line reason.

Use LaTeX for mathematical expressions ($...$ for inline and $$...$$ for display).
Target length: 220-450 words.
"""


async def _generate_solution_text(prompt: str) -> str:
    try:
        from google import genai
    except Exception as exc:
        raise RuntimeError(f"google-genai import failed: {exc}")

    if settings.GOOGLE_CLOUD_PROJECT:
        client = genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )
    elif settings.GEMINI_API_KEY:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
    else:
        raise RuntimeError("Neither Vertex project nor GEMINI_API_KEY is configured")

    model_name = settings.GEMINI_GENERATION_MODEL or "gemini-2.5-flash"

    # SDK call is sync; run in a thread to keep async loop responsive.
    def _call() -> str:
        response = client.models.generate_content(model=model_name, contents=prompt)
        return (response.text or "").strip()

    solution_text = await asyncio.to_thread(_call)
    if len(solution_text.split()) < 60:
        raise RuntimeError("Generated solution too short; skipping write")
    return solution_text


async def process(args: argparse.Namespace) -> None:
    backend_root = Path(__file__).resolve().parent.parent
    yaml_dir = backend_root / "pyq_papers" / args.exam

    if not yaml_dir.exists():
        raise RuntimeError(f"YAML folder not found: {yaml_dir}")

    yaml_files = sorted(yaml_dir.glob("*.yaml"))
    if args.paper_id:
        yaml_files = [p for p in yaml_files if p.stem == args.paper_id]

    if not yaml_files:
        print("No YAML papers found for the given filters.")
        return

    generated = 0
    skipped = 0
    failed = 0
    processed = 0

    for yaml_file in yaml_files:
        with yaml_file.open("r", encoding="utf-8") as f:
            paper = yaml.safe_load(f) or {}

        paper_id = paper.get("id") or yaml_file.stem
        questions = paper.get("questions", []) or []
        print(f"Processing {paper_id}: {len(questions)} questions")

        for q in questions:
            if args.limit and processed >= args.limit:
                print("Reached --limit, stopping.")
                print(
                    f"Summary: generated={generated}, skipped={skipped}, failed={failed}, processed={processed}"
                )
                return

            processed += 1
            q_num = int(q.get("number") or q.get("id") or 0)
            if q_num <= 0:
                failed += 1
                continue

            question_text = str(q.get("text") or "").strip()
            options = {str(k).lower(): v for k, v in (q.get("options") or {}).items()}
            correct_answer = str(q.get("correct_answer") or q.get("correct") or "").strip().lower()

            if not question_text or not options or not correct_answer:
                failed += 1
                continue

            source_hash = _question_hash(question_text, options, correct_answer)
            existing = await PyQSolution.find_one(
                PyQSolution.paper_id == paper_id,
                PyQSolution.question_number == q_num,
            )

            if existing and not args.force:
                if existing.source_hash == source_hash and existing.solution_text.strip():
                    skipped += 1
                    continue

            prompt = _build_prompt(
                question_text=question_text,
                options=options,
                correct_answer=correct_answer,
                section=q.get("section") or q.get("subject"),
                topic=q.get("topic"),
            )

            try:
                solution_text = await _generate_solution_text(prompt)
                now = datetime.now(timezone.utc)

                if existing:
                    existing.question_text = question_text
                    existing.correct_answer = correct_answer
                    existing.solution_text = solution_text
                    existing.source_hash = source_hash
                    existing.provider = "gemini"
                    existing.model_name = settings.GEMINI_GENERATION_MODEL
                    existing.updated_at = now
                    await existing.save()
                else:
                    await PyQSolution(
                        paper_id=paper_id,
                        question_number=q_num,
                        question_text=question_text,
                        correct_answer=correct_answer,
                        solution_text=solution_text,
                        source_hash=source_hash,
                        provider="gemini",
                        model_name=settings.GEMINI_GENERATION_MODEL,
                        created_at=now,
                        updated_at=now,
                    ).insert()

                generated += 1
                if generated % 10 == 0:
                    print(f"Generated so far: {generated}")
            except Exception as exc:
                failed += 1
                print(f"Failed {paper_id} Q{q_num}: {exc}")

    print(
        f"Summary: generated={generated}, skipped={skipped}, failed={failed}, processed={processed}"
    )


async def main() -> None:
    args = parse_args()
    await init_db()
    try:
        await process(args)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
