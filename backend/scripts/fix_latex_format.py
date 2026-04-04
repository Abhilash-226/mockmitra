import asyncio
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
from google.genai import types

from app.core.config import settings
from app.models.question import Question, QuestionSource
import json

async def fix_question_formatting(q: Question, client):
    """Uses Gemini to reformat plain-text math in the question into proper LaTeX."""
    prompt = r"""
You are a math and physics formatting assistant. I will provide you with a multiple-choice question stored in JSON format. The question text, options, correct_option_text, and explanation currently use plain-text math (e.g., sqrt(3), 1/2, a/b, 10^3, x^2+y^2=1). 

Your task is to REFORMAT all mathematical expressions into standard inline LaTeX wrapped seamlessly in single dollar signs `$`. 

RULES:
1. ONLY reformat the math parts into `$` delimiters (e.g., $ \sqrt{3} $, $ \frac{1}{2} $, $ x^2 $).
2. DO NOT change ANY wording, logic, numeric values, or the correct structure.
3. Ensure fractions like 1/\sqrt(3) become $\frac{1}{\sqrt{3}}$.
4. Ensure expressions like (x^4 + x^3 - 5x^2 + 2) / (x^3 - x^2) become $\frac{x^4+x^3-5x^2+2}{x^3-x^2}$.
5. Return exactly the SAME dictionary structure, just with the text fields updated to correct LaTeX. RETURN ONLY VALID JSON. No markdown ticks around it.
6. Escape backslashes if needed so JSON parsing works correctly (e.g., \\sqrt or raw strings).

Original Data:
%s
    """ % json.dumps({
        "question_text": q.question_text,
        "options": list(q.options.values()) if q.options else [],
        "correct_option_text": q.options[q.correct_option] if q.options and q.correct_option in q.options else "",
        "explanation": q.explanation
    }, indent=2)
    
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=settings.GEMINI_GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a strict JSON text formatter. Return valid JSON only.",
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
        )
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        
        fixed_data = json.loads(content)
        
        # update the db object
        if fixed_data.get("question_text"):
            q.question_text = fixed_data["question_text"]
        
        new_opts = fixed_data.get("options", [])
        if len(new_opts) == 4:
            q.options = { 
                "a": new_opts[0], 
                "b": new_opts[1], 
                "c": new_opts[2], 
                "d": new_opts[3] 
            }
            
        cor_opt_text = fixed_data.get("correct_option_text")
        if cor_opt_text:
            for k, v in q.options.items():
                if v == cor_opt_text:
                    q.correct_option = k
                    break

        if fixed_data.get("explanation"):
            q.explanation = fixed_data["explanation"]

        await q.save()
        print(f"✅ Fixed formatting for question ID {q.id}")
    except Exception as e:
        print(f"❌ Failed to fix question ID {q.id}: {e}")

async def main():
    client_db = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(database=client_db[settings.MONGODB_DB_NAME], document_models=[Question])
    print("✅ Connected to MongoDB.")
    
    genai_client = genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION
    )
    
    qs = await Question.find({
        "source": QuestionSource.AI_GENERATED,
    }).to_list()
    
    def needs_fix(q):
        text = str(q.question_text) + str(q.options)
        if '$' in text:
            return False
        if 'sqrt' in text or '^' in text or 'int' in text or 'log' in text or '/' in text:
            return True
        return False
        
    to_fix = [q for q in qs if needs_fix(q)]
    print(f"Found {len(to_fix)} questions that might need LaTeX formatting out of {len(qs)} generated ones.")
    
    batch_size = 5
    for i in range(0, len(to_fix), batch_size):
        chunk = to_fix[i:i+batch_size]
        tasks = [fix_question_formatting(q, genai_client) for q in chunk]
        await asyncio.gather(*tasks)
        print(f"Batch {i//batch_size + 1} completed. Waiting 2s...")
        await asyncio.sleep(2)
        
    print("🎉 Formatting fix complete!")

if __name__ == "__main__":
    asyncio.run(main())
