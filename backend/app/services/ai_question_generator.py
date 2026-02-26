import os
import json
import random
import time
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid

from google import genai
from google.genai import types

from app.models.blueprint import (
    Blueprint,
    GeneratedQuestion,
    DifficultyLevel
)
from app.core.config import settings

# =============================================================================
# DATA MODELS
# =============================================================================

class AIQuestionOutput(BaseModel):
    """Structure expected from the LLM."""
    question_text: str = Field(..., description="The full text of the question")
    options: List[str] = Field(..., description="List of 4 distinct options")
    correct_option: str = Field(..., description="The correct answer (must be one of the options)")
    solution_steps: Union[str, List[str]] = Field(..., description="Step-by-step solution to derive the answer")
    variables: Dict[str, Any] = Field(..., description="Key-value pairs of variables used (if any)")
    reasoning: Optional[str] = Field(None, description="Brief explanation of why this question is valid")

    @field_validator('solution_steps')
    def validate_solution_steps(cls, v):
        if isinstance(v, list):
            return "\n".join(v)
        return v

# =============================================================================
# GEMINI AI GENERATOR SERVICE
# =============================================================================

class AIQuestionGenerator:
    """
    Generates exam questions using Gemini 1.5 Flash via Google GenAI SDK.
    Uses GCP credits if GOOGLE_CLOUD_PROJECT is set, otherwise uses API Key.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.project = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.GOOGLE_CLOUD_LOCATION
        self.client = None
        self.model = "gemini-2.0-flash-001" 
        
        try:
            if self.project:
                # Use Vertex AI (GCP Credits)
                print(f"Initializing Gemini via Vertex AI (Project: {self.project})")
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location
                )
                # Vertex AI uses a different model name format
                self.model = "gemini-2.0-flash-001"
            elif self.api_key:
                # Use API Key (AI Studio style)
                print("Initializing Gemini via API Key")
                self.client = genai.Client(api_key=self.api_key)
            else:
                print("AI Generator Error: No Gemini API Key or GCP Project provided.")
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")

    def generate_question(
        self, 
        blueprint: Blueprint, 
        difficulty: Optional[DifficultyLevel] = None
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a single unique question from a blueprint using Gemini.
        """
        if not self.client:
            print("AI Generator Error: Client not initialized.")
            return None

        difficulty = difficulty or blueprint.difficulty_level or DifficultyLevel.MODERATE
        
        # 1. Construct Prompt
        system_prompt, user_prompt = self._build_prompts(blueprint, difficulty)
        
        # 2. Call Gemini
        try:
            response_json = self._call_gemini(system_prompt, user_prompt)
            if not response_json:
                return None
            
            # 3. Parse & Validate Structure
            ai_data = AIQuestionOutput(**response_json)
            
            # 4. Convert to Domain Model
            return self._convert_to_question(ai_data, blueprint, difficulty)
            
        except Exception as e:
            print(f"Gemini Generation Failed for {blueprint.id}: {e}")
            return None

    def _build_prompts(self, blueprint: Blueprint, difficulty: DifficultyLevel) -> tuple[str, str]:
        """Constructs prompts for Gemini."""
        
        section = blueprint.section or blueprint.chapter or "General"
        topic = blueprint.topic or blueprint.concept or "General"
        
        # Handle difficulty
        diff_str = str(difficulty.value if hasattr(difficulty, 'value') else difficulty).upper()

        # Handle Template/Reference
        template_str = ""
        is_pyq = "pyq_source" in (blueprint.tags or [])
        
        if is_pyq:
            template_str = f"REFERENCE PYQ QUESTION (Original): {blueprint.template}\nINSTRUCTION: Create a NEW question based on the CONCEPT of this PYQ. Change values, scenarios, or chemical compounds. Do NOT repeat the reference question."
        elif blueprint.template_variants:
            template_str = f"TEMPLATE: {random.choice(blueprint.template_variants)}"
        else:
            template_str = f"TEMPLATE: {blueprint.template}"

        system_prompt = f"""You are an expert Professor setting questions for the {blueprint.exam} exam ({blueprint.subject}).
Your task is to generate a original, challenging, and accurate Multiple Choice Question (MCQ) based on a specific blueprint/template.

Target Exam: {blueprint.exam}
Subject: {blueprint.subject}
Difficulty: {diff_str}
Section/Topic: {section} / {topic}

STRICT TECHNICAL RULES:
1. Accuracy: The question must be mathematically and scientifically flawless.
2. LaTeX: Use $...$ for all mathematical expressions and chemical formulas. Example: $\\text{{H}}_2\\text{{SO}}_4$, $x^2 + 2x + 1$.
3. Originality: If a reference question is provided, do NOT repeat it. Extract the CORE CONCEPT and create a new problem.
4. Distractors: Provide 4 plausible options. Avoid "None of these" or "All of these".
5. Language: Use professional, academic English.
6. JSON: Output ONLY a valid JSON object. No conversation, no markdown blocks.
7. Backslashes: In the JSON output, all backslashes in LaTeX must be properly escaped (e.g., use \\\\text instead of \\text).
"""

        user_prompt = f"""Generate a unique {diff_str} question for:
Subject: {blueprint.subject}
Topic: {topic}
{template_str}

Ensure the output matches this schema:
{{
  "question_text": "string (including LaTeX)",
  "options": ["string", "string", "string", "string"],
  "correct_option": "string (must match one in options exactly)",
  "solution_steps": "string (detailed explanation)",
  "variables": {{ "name": value }},
  "reasoning": "string (internal logic)"
}}
"""
        return system_prompt, user_prompt

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call Gemini API using the new SDK with exponential backoff for 429s."""
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                        response_mime_type="application/json"
                    )
                )
                
                # Pre-processing: Sometimes LLMs return extra escapes or slightly broken JSON
                content = response.text.strip()
                # Remove markdown code blocks if present
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                import re

                # PRE-PROCESS: Always double single backslashes before JSON parsing.
                # Critical: LaTeX commands like \neq, \notin, \text, \frac, \begin
                # start with valid JSON escape chars (\n, \t, \f, \b). json.loads
                # "silently succeeds" - turning \neq into newline+"eq" - without
                # raising any error, so an except-block fix would never fire.
                # The regex only doubles truly-single backslashes; already-doubled
                # ones (e.g. \\\\frac that Gemini got right) are left untouched.
                content = re.sub(r'(?<!\\\\)\\\\(?!\\\\)', r'\\\\\\\\', content)

                try:
                    return json.loads(content)
                except json.JSONDecodeError as je:
                    print(f"JSON Decode Error (after backslash pre-processing).")
                    raise je  # Triggers the retry / error handler below

            except Exception as e:
                error_msg = str(e)
                # Handle Rate Limiting (429)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Gemini Rate Limit (429). Retrying in {delay:.2f}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    continue
                
                # Handle JSON issues (escape problems AND invalid control characters like \b)
                if ("JSONDecodeError" in error_msg or "Invalid \\escape" in error_msg
                        or "Invalid control character" in error_msg):
                    print(f"Gemini returning invalid JSON (escape/control char issue). Retrying... ({attempt+1}/{max_retries})")
                    time.sleep(1)  # Small pause
                    continue
                    
                print(f"Gemini API Call Error: {e}")
                return None
        
        return None

    def _convert_to_question(
        self, 
        ai_data: AIQuestionOutput, 
        blueprint: Blueprint,
        difficulty: DifficultyLevel
    ) -> GeneratedQuestion:
        """Converts raw AI output to internal Question model."""
        
        # Find correct index
        try:
            correct_idx = ai_data.options.index(ai_data.correct_option)
        except ValueError:
            # Fallback for LLM mistakes
            correct_idx = 0
            ai_data.options[0] = ai_data.correct_option
            
        return GeneratedQuestion(
            id=str(uuid.uuid4()),
            blueprint_id=blueprint.id,
            question_text=ai_data.question_text,
            options=ai_data.options,
            correct_answer=ai_data.correct_option,
            correct_option_index=correct_idx,
            solution=ai_data.solution_steps,
            variables_used=ai_data.variables,
            difficulty_level=difficulty,
            subject=blueprint.subject,
            chapter=blueprint.chapter,
            concept=blueprint.concept,
            tags=(blueprint.tags or []) + ["gemini_generated"],
            generated_at=datetime.utcnow()
        )
