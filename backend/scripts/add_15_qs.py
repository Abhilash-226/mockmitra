import asyncio
import os
import sys

# make sure backend/ is on sys.path
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.models.question import Question
from scripts.seed_question_pool import load_exam_structure, load_pyq_questions, seed_topic
from app.services.question_generator_v2 import get_question_generator_v2

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[Question],
    )
    print("✅ Connected to MongoDB.")

    entries = load_exam_structure("ts_eamcet")
    all_pyqs = load_pyq_questions("ts_eamcet")
    pyq_by_topic = {}
    for q in all_pyqs:
        t = q.get("topic", "")
        s = q.get("section", "")
        for key in (t, s):
            if key:
                pyq_by_topic.setdefault(key, []).append(q)

    generator = get_question_generator_v2()

    # Targets
    targets = {
        "Algebra": 15,
        "Trigonometry": 15
    }

    for target_section, needed in targets.items():
        print(f"\n--- Running for section: {target_section} ---")
        section_entries = [e for e in entries if e["section"].lower() == target_section.lower()]
        
        # Distribute 'needed' questions across the topics in the section.
        topics_count = len(section_entries)
        base_per_topic = needed // topics_count
        remainder = needed % topics_count
        
        inserted_total = 0
        for i, entry in enumerate(section_entries):
            target_for_topic = base_per_topic + (1 if i < remainder else 0)
            if target_for_topic == 0:
                continue
                
            print(f"\n  -> Generating {target_for_topic} for {entry['topic']}")
            
            inserted = await seed_topic(
                exam_code="ts_eamcet",
                subject=entry["subject"],
                section=entry["section"],
                topic=entry["topic"],
                target=target_for_topic,
                pyq_by_topic=pyq_by_topic,
                generator=generator,
                dry_run=False,
                resume=False
            )
            inserted_total += inserted
            
        print(f"\n✅ Finished {target_section}: inserted {inserted_total} questions.")

if __name__ == "__main__":
    asyncio.run(main())
