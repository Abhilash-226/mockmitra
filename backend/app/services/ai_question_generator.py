import os
import json
import ast
import random
import time
import threading
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

    _semaphore_lock = threading.Lock()
    _global_semaphore = None
    _global_semaphore_capacity = None
    _rate_limit_lock = threading.Lock()
    _last_call_at = 0.0
    _cooldown_lock = threading.Lock()
    _cooldown_until = 0.0
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.project = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.GOOGLE_CLOUD_LOCATION
        self.client = None
        self.model = settings.GEMINI_GENERATION_MODEL
        self.generator_max_calls_per_second = max(0.0, float(settings.GENERATOR_MAX_CALLS_PER_SECOND))
        self.generator_429_cooldown_seconds = max(0, int(settings.GENERATOR_429_COOLDOWN_SECONDS))
        self._ensure_global_semaphore()
        
        try:
            if self.project:
                # Use Vertex AI (GCP Credits)
                print(
                    f"Initializing Gemini via Vertex AI (Project: {self.project}, Model: {self.model})"
                )
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location
                )
            elif self.api_key:
                # Use API Key (AI Studio style)
                print(f"Initializing Gemini via API Key (Model: {self.model})")
                self.client = genai.Client(api_key=self.api_key)
            else:
                print("AI Generator Error: No Gemini API Key or GCP Project provided.")
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")

    def _ensure_global_semaphore(self):
        capacity = max(1, int(settings.GENERATOR_GLOBAL_CONCURRENCY))
        if (
            AIQuestionGenerator._global_semaphore is not None
            and AIQuestionGenerator._global_semaphore_capacity == capacity
        ):
            return

        with AIQuestionGenerator._semaphore_lock:
            if (
                AIQuestionGenerator._global_semaphore is None
                or AIQuestionGenerator._global_semaphore_capacity != capacity
            ):
                AIQuestionGenerator._global_semaphore = threading.BoundedSemaphore(value=capacity)
                AIQuestionGenerator._global_semaphore_capacity = capacity

    def _respect_cooldown(self):
        with AIQuestionGenerator._cooldown_lock:
            wait_seconds = max(0.0, AIQuestionGenerator._cooldown_until - time.monotonic())
        if wait_seconds > 0:
            print(f"Generator cooldown active ({wait_seconds:.1f}s) due to recent 429")
            time.sleep(wait_seconds)

    def _register_rate_limit_hit(self):
        if self.generator_429_cooldown_seconds <= 0:
            return
        with AIQuestionGenerator._cooldown_lock:
            AIQuestionGenerator._cooldown_until = max(
                AIQuestionGenerator._cooldown_until,
                time.monotonic() + self.generator_429_cooldown_seconds,
            )

    def _wait_for_rate_limit_slot(self):
        if self.generator_max_calls_per_second <= 0:
            return

        min_interval = 1.0 / self.generator_max_calls_per_second
        while True:
            with AIQuestionGenerator._rate_limit_lock:
                now = time.monotonic()
                elapsed = now - AIQuestionGenerator._last_call_at
                if elapsed >= min_interval:
                    AIQuestionGenerator._last_call_at = now
                    return
                wait_seconds = min_interval - elapsed
            time.sleep(min(wait_seconds, 0.25))

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
1. Accuracy: The question must be mathematically and scientifically flawless. SOLVE THE PROBLEM FULLY FIRST, then generate the options.
2. Formatting: You MUST use proper standard LaTeX for all mathematical expressions, variables, formulas, and equations. Inline math MUST be enclosed in single dollar signs (e.g., $\sqrt{{3}}$, $x^2$, $\frac{{a+b}}{{c}}$). Block math MUST be enclosed in double dollar signs. NEVER use plain-text math like sqrt(3) or 1/2 or m-1.
3. Originality: If a reference question is provided, do NOT repeat it. Extract the CORE CONCEPT and create a new problem.
4. Distractors: Provide 4 plausible options. Avoid "None of these" or "All of these".
5. Language: Use professional, academic English.
6. JSON: Output ONLY a valid JSON object. No conversation, no markdown blocks.
7. Backslashes: In the JSON output, all backslashes in LaTeX must be properly escaped (e.g., use \\\\frac instead of \\frac).

CRITICAL - CORRECT ANSWER REQUIREMENT:
- You MUST first solve the problem completely and arrive at a NUMERICAL or EXACT answer.
- Then create 4 options where ONE option contains EXACTLY this computed answer.
- The correct_option field MUST be COPIED EXACTLY (character-for-character) from one of the 4 strings in the options array.
- Do NOT compute one answer in solution_steps but put a different value in correct_option.
- COMMON MISTAKES TO AVOID:
  * Conservation of momentum: Check signs and magnitudes carefully.
  * Kinematics with direction changes: Use absolute values for distance (not displacement).
  * Integration: Be careful with limits and signs when velocity changes direction.
  * Surface area/energy: Double-check exponents and orders of magnitude.
- After computing the answer, VERIFY it by substituting back or checking units/dimensions.
- Verify: correct_option == options[i] for exactly one i in [0,1,2,3].
"""

        user_prompt = f"""Generate a unique {diff_str} question for:
Subject: {blueprint.subject}
Topic: {topic}
{template_str}

MANDATORY WORKFLOW - Follow these steps IN ORDER:
1. First, create the question with specific numerical values.
2. SOLVE the problem completely step-by-step. Show ALL intermediate calculations.
3. Arrive at a final numerical/exact answer. CHECK your arithmetic by re-computing.
4. Create 4 options: ONE must be EXACTLY your computed answer, the other 3 must be plausible wrong answers (common student mistakes like sign errors, missing factors, wrong formulas).
5. Set correct_option to the EXACT string from the options array that matches the computed answer.
6. SELF-CHECK: Verify correct_option appears character-for-character in the options array.

Ensure the output matches this schema:
{{
    "question_text": "string",
  "options": ["string", "string", "string", "string"],
  "correct_option": "string (MUST be exactly copied from one of the 4 options above)",
  "solution_steps": "string (detailed step-by-step solution showing how you arrive at the answer, including verification)",
  "variables": {{ "name": value }},
  "reasoning": "string (internal logic)"
}}
"""
        return system_prompt, user_prompt

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call Gemini API with robust JSON parsing for LaTeX-heavy math content."""
        max_retries = 3
        base_delay = 2
        semaphore = AIQuestionGenerator._global_semaphore
        if semaphore:
            semaphore.acquire()

        try:
            for attempt in range(max_retries):
                try:
                    self._respect_cooldown()
                    self._wait_for_rate_limit_slot()
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.2,
                            response_mime_type="application/json"
                        )
                    )

                    content = response.text.strip()
                    if content.startswith("```json"):
                        content = content[7:-3].strip()
                    elif content.startswith("```"):
                        content = content[3:-3].strip()

                    result = self._parse_json_response(content)
                    if result is not None:
                        result = self._fix_latex_in_parsed(result)
                        return result

                    print(f"JSON parse failed after all strategies, attempt {attempt+1}/{max_retries}")
                    time.sleep(1)
                    continue

                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        self._register_rate_limit_hit()
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Gemini Rate Limit (429). Retrying in {delay:.2f}s... ({attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    print(f"Gemini API Call Error: {e}")
                    return None
        finally:
            if semaphore:
                semaphore.release()
        
        return None

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """Parse JSON with multiple fallback strategies for LaTeX-heavy math content."""
        import re
        
        # Strategy 1: Direct parse (works for well-formed responses)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Allow control characters in strings (strict=False)
        try:
            return json.JSONDecoder(strict=False).decode(content)
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Remove literal control chars + fix invalid backslash escapes
        cleaned = re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        fixed = re.sub(r'\\(?!["\\\\/{bfnrtu])', r'\\\\', cleaned)
        try:
            return json.JSONDecoder(strict=False).decode(fixed)
        except json.JSONDecodeError:
            pass
        
        # Strategy 4: Aggressive - double ALL single backslashes
        sanitized = self._sanitize_all_backslashes(cleaned)
        try:
            return json.JSONDecoder(strict=False).decode(sanitized)
        except json.JSONDecodeError:
            pass
        
        # Strategy 5: Extract JSON object from surrounding text (handles markdown/preamble)
        try:
            # Find the outermost { ... } block
            brace_start = cleaned.find('{')
            brace_end = cleaned.rfind('}')
            if brace_start != -1 and brace_end > brace_start:
                json_substr = cleaned[brace_start:brace_end + 1]
                # Try parsing the extracted block with backslash fix
                fixed_substr = re.sub(r'\\(?!["\\\\/{bfnrtu])', r'\\\\', json_substr)
                return json.JSONDecoder(strict=False).decode(fixed_substr)
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 6: Python-dict style fallback (single quotes / True / False)
        try:
            python_obj = ast.literal_eval(content)
            if isinstance(python_obj, dict):
                return python_obj
        except Exception:
            pass

        # Strategy 7: Extract dict-like block then literal_eval
        try:
            brace_start = content.find('{')
            brace_end = content.rfind('}')
            if brace_start != -1 and brace_end > brace_start:
                dict_substr = content[brace_start:brace_end + 1]
                python_obj = ast.literal_eval(dict_substr)
                if isinstance(python_obj, dict):
                    return python_obj
        except Exception:
            pass
        
        return None

    def _sanitize_all_backslashes(self, text: str) -> str:
        """Double all single backslashes - aggressive fix for LaTeX in JSON."""
        result = []
        i = 0
        while i < len(text):
            if text[i] == '\\':
                if i + 1 < len(text) and text[i+1] == '\\':
                    result.append('\\\\')
                    i += 2
                elif i + 1 < len(text) and text[i+1] == '"':
                    result.append('\\"')
                    i += 2
                else:
                    result.append('\\\\')
                    i += 1
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    def _fix_latex_in_parsed(self, data: Dict) -> Dict:
        """Restore LaTeX commands mangled by JSON escape interpretation.
        
        JSON interprets \\f as form feed, \\b as backspace, etc.
        This restores them to LaTeX backslash commands when followed by letters.
        """
        import re

        def cleanup_subsuperscript_dollars(s: str) -> str:
            """Fix malformed dollars around sub/superscripts.

            Examples:
            - t_{2$g$} -> t_{2g}
            - t_$g$ -> t_{g}
            """
            if not s:
                return s

            # Convert _${...}$ style fragments to braced sub/superscripts
            s = re.sub(r'([_^])\$([^$]+)\$', r'\1{\2}', s)

            # Remove stray $ inside already-braced sub/superscripts
            def _strip_inner_dollars(match):
                prefix, inner, suffix = match.groups()
                return f"{prefix}{inner.replace('$', '')}{suffix}"

            previous = None
            while previous != s:
                previous = s
                s = re.sub(r'([_^]\{)([^{}]*)(\})', _strip_inner_dollars, s)

            return s
        
        def fix_text(s):
            if not isinstance(s, str):
                return s
            s = re.sub('\x0c([a-zA-Z])', r'\\f\1', s)   # form feed -> \f (\frac, \forall)
            s = re.sub('\x08([a-zA-Z])', r'\\b\1', s)   # backspace -> \b (\begin, \binom)
            s = re.sub('\x09([a-zA-Z])', r'\\t\1', s)   # tab -> \t (\text, \theta)
            s = re.sub('\x0d([a-zA-Z])', r'\\r\1', s)   # CR -> \r (\right, \rangle)
            s = re.sub('\x0a([a-z])', r'\\n\1', s)      # newline -> \n (\neq, \nu)
            s = cleanup_subsuperscript_dollars(s)
            return s
        
        for key in ['question_text', 'correct_option', 'reasoning']:
            if key in data and isinstance(data[key], str):
                data[key] = fix_text(data[key])
        
        if 'options' in data and isinstance(data['options'], list):
            data['options'] = [fix_text(o) if isinstance(o, str) else o for o in data['options']]
        
        if 'solution_steps' in data:
            if isinstance(data['solution_steps'], str):
                data['solution_steps'] = fix_text(data['solution_steps'])
            elif isinstance(data['solution_steps'], list):
                data['solution_steps'] = [fix_text(s) if isinstance(s, str) else s for s in data['solution_steps']]
        
        return data

    def _normalize_option_text(self, text: str) -> str:
        """Normalize option text for comparison (strip whitespace, normalize LaTeX)."""
        import re
        t = text.strip()
        # Remove surrounding $...$ for comparison
        t = re.sub(r'^\$(.+)\$$', r'\1', t)
        # Normalize whitespace
        t = re.sub(r'\s+', ' ', t)
        # Normalize common LaTeX variants (use raw strings to avoid escape issues)
        t = t.replace(r'\frac', 'FRAC').replace(r'\text', 'TEXT')
        t = t.replace(r'\sqrt', 'SQRT').replace(r'\ln', 'LN')
        return t.lower()

    def _convert_to_question(
        self, 
        ai_data: AIQuestionOutput, 
        blueprint: Blueprint,
        difficulty: DifficultyLevel
    ) -> Optional[GeneratedQuestion]:
        """Converts raw AI output to internal Question model.
        
        Returns None if the correct answer cannot be reliably matched to an option.
        """
        
        if not ai_data.options or len(ai_data.options) < 4:
            print(f"VALIDATION FAIL: Less than 4 options generated")
            return None
        
        # Check for duplicate options
        unique_options = set(ai_data.options)
        if len(unique_options) < 4:
            print(f"VALIDATION FAIL: Duplicate options detected: {ai_data.options}")
            return None

        # Step 1: Try exact match
        correct_idx = None
        try:
            correct_idx = ai_data.options.index(ai_data.correct_option)
        except ValueError:
            pass
        
        # Step 2: Try normalized/fuzzy match
        if correct_idx is None:
            norm_correct = self._normalize_option_text(ai_data.correct_option)
            for i, opt in enumerate(ai_data.options):
                if self._normalize_option_text(opt) == norm_correct:
                    correct_idx = i
                    print(f"VALIDATION FIX: Fuzzy matched correct_option to options[{i}]")
                    break
        
        # Step 3: Try substring match (e.g., "-3/5" in "$-\frac{3}{5}$")
        if correct_idx is None:
            norm_correct = self._normalize_option_text(ai_data.correct_option)
            for i, opt in enumerate(ai_data.options):
                norm_opt = self._normalize_option_text(opt)
                if norm_correct in norm_opt or norm_opt in norm_correct:
                    correct_idx = i
                    print(f"VALIDATION FIX: Substring matched correct_option to options[{i}]")
                    break
        
        # Step 4: If still no match, REJECT the question — don't silently insert
        if correct_idx is None:
            print(f"VALIDATION FAIL: correct_option '{ai_data.correct_option}' not found in options {ai_data.options}")
            print(f"Rejecting question to trigger retry with fresh generation.")
            return None
            
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
