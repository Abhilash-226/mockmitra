import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path("c:/Users/ashad/Desktop/abhilash/Projects/MockMitra/backend")
sys.path.append(str(backend_path))

import asyncio
from app.services.ai_question_generator import AIQuestionGenerator
from app.models.blueprint import Blueprint, DifficultyLevel, AnswerType

async def test_gemini():
    print("Testing Gemini 1.5 Flash via Vertex AI...")
    
    # Mock a blueprint
    test_bp = Blueprint(
        id="TEST_BP_001",
        subject="Chemistry",
        section="Organic Chemistry",
        topic="Hydrocarbons",
        template="What is the product P in the following reaction: Propyne + HgSO4/dil. H2SO4 -> P?",
        difficulty_level=DifficultyLevel.MODERATE,
        answer_type=AnswerType.CATEGORICAL,
        answer_options=["Acetone", "Propanol", "Propanal", "Acetic acid"],
        tags=["pyq_source", "test"]
    )
    
    generator = AIQuestionGenerator()
    print(f"Generator initialized with project: {generator.project}")
    
    # Debug: List available models
    print("\n--- AVAILABLE MODELS ---")
    try:
        for model in generator.client.models.list():
            if "flash" in model.name.lower():
                print(f"- {model.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
    print("------------------------\n")
    
    question = generator.generate_question(test_bp)
    
    if question:
        print("\n--- GENERATED QUESTION ---")
        print(f"Text: {question.question_text}")
        print(f"Options: {question.options}")
        print(f"Correct: {question.correct_answer}")
        print(f"Solution: {question.solution}")
        print("--------------------------\n")
        print("SUCCESS: Gemini is working!")
    else:
        print("FAILURE: Could not generate question.")

if __name__ == "__main__":
    asyncio.run(test_gemini())
