import os
import json
import random
import time
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid

import groq
from groq import Groq

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
# AI GENERATOR SERVICE
# =============================================================================

class AIQuestionGenerator:
    """
    Generates exam questions using Groq/Llama-3 based on structured blueprints.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = None
        self.model = "llama-3.1-8b-instant"  # Using 8B for speed/cost balance
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize Groq client: {e}")

    def generate_question(
        self, 
        blueprint: Blueprint, 
        difficulty: Optional[DifficultyLevel] = None
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a single unique question from a blueprint using AI.
        """
        if not self.client:
            print("AI Generator Error: No API Key provided.")
            return None

        difficulty = difficulty or blueprint.difficulty_level or DifficultyLevel.MODERATE
        
        # 1. Construct Prompt
        prompt = self._build_prompt(blueprint, difficulty)
        
        # 2. Call LLM
        try:
            response_json = self._call_llm(prompt)
            if not response_json:
                print(f"LLM returned no JSON for {blueprint.id}")
                return None
            
            # DEBUG: Dump JSON
            with open("debug_response.json", "w", encoding="utf-8") as f:
                json.dump(response_json, f, indent=2)

            # 3. Parse & Validate Structure
            ai_data = AIQuestionOutput(**response_json)
            
            # 4. Convert to Domain Model
            return self._convert_to_question(ai_data, blueprint, difficulty)
            
        except Exception as e:
            print(f"AI Generation Failed for {blueprint.id}: {e}")
            import traceback
            with open("ai_gen_error.log", "w") as f:
                traceback.print_exc(file=f)
            return None

    def _build_prompt(self, blueprint: Blueprint, difficulty: DifficultyLevel) -> str:
        """Constructs the system and user prompt for the LLM."""
        
        # Use new hierarchy with fallbacks
        section = blueprint.section or blueprint.chapter or "General"
        topic = blueprint.topic or blueprint.concept or "General"

        # Extra metadata for few-shot prompts
        source_id = ""
        if "pyq_source" in (blueprint.tags or []):
            source_id = next((t for t in blueprint.tags if "ts_eamcet" in t), "")

        # Handle difficulty enum or string
        diff_str = "MODERATE"
        if hasattr(difficulty, 'value'):
            diff_str = difficulty.value.upper()
        else:
            diff_str = str(difficulty).upper()

        # Extract template or concept description
        template_str = ""
        if blueprint.template_variants:
            template_str = f"Template Example: {random.choice(blueprint.template_variants)}"
        elif blueprint.template:
            # Check if this is a virtual blueprint (few-shot guide)
            if "pyq_source" in (blueprint.tags or []):
                template_str = f"Reference Real Exam Question (DO NOT REPEAT, USE AS STYLE GUIDE): {blueprint.template}"
            else:
                template_str = f"Template Example: {blueprint.template}"
            
        system_prompt = f"""You are an expert exam setter for {blueprint.exam}.
Your task is to generate a UNIQUE, HIGH-QUALITY {blueprint.subject} question based on a specific blueprint.

**Constraints:**
1. Difficulty: {diff_str}
2. Section: {section}
3. Topic: {topic}
4. Question Type: Multiple Choice (4 Options)
5. Output Format: STRICT JSON ONLY. No markdown, no preamble.

**Rules:**
1. The question must be mathematically/scientifically accurate.
2. Generate NEW numbers/scenarios. Do NOT copy the reference/template exactly.
3. If a reference question is provided, analyze its complexity and logical depth, then create a target question of EQUAL depth but DIFFERENT application.
4. Ensure the options are plausible distractors.
5. The 'correct_option' must be exactly one of the values in 'options'.
6. 'solution_steps' must explain the logic clearly.
7. Be creative! Use different names, contexts, or physical setups to ensure variety.
"""

        user_prompt = f"""
Generate a question for:
Subject: {blueprint.subject}
Section: {section}
Topic: {topic}
{template_str}

Output JSON structure:
{{
  "question_text": "...",
  "options": ["A", "B", "C", "D"],
  "correct_option": "...",
  "solution_steps": "...",
  "variables": {{ "var_name": value }},
  "reasoning": "..."
}}
"""
        return system_prompt + "\n\nUser Request:\n" + user_prompt

    def _call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Executes the request to Groq SDK."""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                temperature=0.85, # Increased for better variety
                response_format={"type": "json_object"},
            )
            
            content = chat_completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"LLM Call Error: {e}")
            return None

    def _convert_to_question(
        self, 
        ai_data: AIQuestionOutput, 
        blueprint: Blueprint,
        difficulty: DifficultyLevel
    ) -> GeneratedQuestion:
        """Converts raw AI output to internal Question model."""
        
        # Find correct index
        correct_idx = 0
        correct_display = ai_data.correct_option
        
        # Scenario 1: correct_option is "A", "B", "C", "D"
        if ai_data.correct_option.upper() in ["A", "B", "C", "D"]:
            mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
            correct_idx = mapping[ai_data.correct_option.upper()]
            if correct_idx < len(ai_data.options):
                correct_display = ai_data.options[correct_idx]
        
        # Scenario 2: correct_option is the actual text
        else:
            try:
                correct_idx = ai_data.options.index(ai_data.correct_option)
                correct_display = ai_data.correct_option
            except ValueError:
                # Fallback: fuzzy match? For now default to 0
                correct_idx = 0
                correct_display = ai_data.options[0] if ai_data.options else "N/A"
            
        return GeneratedQuestion(
            id=str(uuid.uuid4()),
            blueprint_id=blueprint.id,
            question_text=ai_data.question_text,
            options=ai_data.options,
            correct_answer=correct_display,
            correct_option_index=correct_idx,
            solution=ai_data.solution_steps,
            variables_used=ai_data.variables,
            difficulty_level=difficulty,
            subject=blueprint.subject,
            chapter=blueprint.chapter,
            concept=blueprint.concept,
            tags=blueprint.tags or [],
            generated_at=datetime.utcnow()
        )
