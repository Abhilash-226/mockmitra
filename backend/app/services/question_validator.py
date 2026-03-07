import json
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

try:
    from groq import Groq
except ImportError:
    Groq = None

from google import genai
from google.genai import types

from app.models.blueprint import GeneratedQuestion, Blueprint
from app.core.config import settings

class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="True if the question is logically sound")
    computed_answer: Optional[str] = Field(None, description="The answer the solver computed")
    claimed_answer_is_correct: Optional[bool] = Field(None, description="Does the claimed answer match the computed answer?")
    reason: str = Field(..., description="Explanation of validity or failure")
    corrected_answer: Optional[str] = Field(None, description="If valid but answer was wrong, the correct answer")

class QuestionValidator:
    """
    Validates AI-generated questions:
    1. Structural validation (always on) - checks options, correct answer, duplicates
    2. AI solver validation (uses Gemini to independently solve and verify)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.gemini_client = None
        self.gemini_model = "gemini-2.0-flash-001"
        
        # Initialize Gemini for AI solver validation
        project = settings.GOOGLE_CLOUD_PROJECT
        location = settings.GOOGLE_CLOUD_LOCATION
        try:
            if project:
                self.gemini_client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=location
                )
            elif settings.GEMINI_API_KEY:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            print(f"Validator Gemini Init Failed: {e}")

    def validate_question(self, question: GeneratedQuestion, blueprint: Blueprint) -> bool:
        """
        Validates the question. Always runs structural checks.
        Then uses Gemini to independently solve and verify the answer.
        If the AI solver finds a wrong answer but can correct it, the question
        object is mutated in-place with the corrected answer.
        Returns True if the question passes all checks (possibly after correction).
        """
        # 1. ALWAYS run structural validation
        structural_result = self._structural_validate(question)
        if not structural_result["is_valid"]:
            print(f"STRUCTURAL VALIDATION FAILED for {question.id}: {structural_result['errors']}")
            return False
        
        if structural_result["warnings"]:
            print(f"STRUCTURAL WARNINGS for {question.id}: {structural_result['warnings']}")

        # 2. Run AI solver validation using Gemini
        if self.gemini_client:
            return self._ai_validate(question, blueprint)
        
        return True

    def _structural_validate(self, question: GeneratedQuestion) -> Dict[str, Any]:
        """
        Non-AI structural validation. Always enabled.
        Checks:
        - Has 4 distinct options
        - Correct answer exists in option list
        - No empty/placeholder options
        - Question text is non-trivial
        """
        errors = []
        warnings = []
        
        # Check question text
        if not question.question_text or len(question.question_text.strip()) < 10:
            errors.append("Question text is too short or empty")
        
        # Check options count
        if not question.options or len(question.options) < 4:
            errors.append(f"Expected 4 options, got {len(question.options) if question.options else 0}")
        
        if question.options and len(question.options) >= 4:
            # Check for empty/placeholder options
            for i, opt in enumerate(question.options):
                if not opt or opt.strip() == "":
                    errors.append(f"Option {i} is empty")
                elif opt.strip().lower() in ["option a", "option b", "option c", "option d"]:
                    errors.append(f"Option {i} is a placeholder: '{opt}'")
            
            # Check for duplicate options (normalized)
            normalized = [self._normalize(o) for o in question.options]
            if len(set(normalized)) < len(normalized):
                # Find the duplicates
                seen = set()
                dupes = []
                for n in normalized:
                    if n in seen:
                        dupes.append(n)
                    seen.add(n)
                errors.append(f"Duplicate options detected: {dupes}")
            
            # Check correct answer is in options
            correct = question.correct_answer
            if correct:
                exact_match = correct in question.options
                norm_match = self._normalize(correct) in normalized
                
                if not exact_match and not norm_match:
                    errors.append(
                        f"Correct answer '{correct[:50]}' not found in options. "
                        f"Options: {[o[:30] for o in question.options]}"
                    )
                elif not exact_match and norm_match:
                    warnings.append("Correct answer matched via normalization (not exact)")
            else:
                errors.append("No correct_answer specified")
            
            # Check correct_option_index is valid
            if question.correct_option_index is not None:
                if question.correct_option_index < 0 or question.correct_option_index >= len(question.options):
                    errors.append(f"correct_option_index {question.correct_option_index} out of range")
                elif question.options[question.correct_option_index] != correct:
                    # Index doesn't point to the correct answer text
                    norm_at_idx = self._normalize(question.options[question.correct_option_index])
                    norm_correct = self._normalize(correct)
                    if norm_at_idx != norm_correct:
                        errors.append(
                            f"correct_option_index {question.correct_option_index} points to "
                            f"'{question.options[question.correct_option_index][:30]}' but correct_answer is '{correct[:30]}'"
                        )
        
        # Check solution exists
        if not question.solution or len(str(question.solution).strip()) < 10:
            warnings.append("Solution is missing or too short")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        t = text.strip()
        # Remove surrounding $ for LaTeX
        t = re.sub(r'^\$(.+)\$$', r'\1', t)
        # Collapse whitespace
        t = re.sub(r'\s+', ' ', t)
        return t.lower()

    def _ai_validate(self, question: GeneratedQuestion, blueprint: Blueprint) -> bool:
        """AI solver validation - uses Gemini to independently solve and verify the answer.
        
        If the solver finds the claimed answer is wrong but provides a corrected_answer
        that matches one of the existing options, the question is corrected in-place.
        
        Includes sanity-check: if solver says invalid but its own reasoning/corrected_answer
        confirms the claimed answer, override to valid (guards against LLM hallucination).
        """
        prompt = self._build_solver_prompt(question)
        
        try:
            response = self._call_gemini_solver(prompt)
            if not response:
                print("Validator: No response from Gemini solver")
                return True  # Fail open - structural already passed
                
            validation = ValidationResult(**response)
            
            print(f"AI Solver Result: valid={validation.is_valid}, claimed_correct={validation.claimed_answer_is_correct}, computed={validation.computed_answer}")

            # Sanity check: detect hallucinated rejections
            # If solver says invalid BUT its own fields confirm the answer is correct, override
            if not validation.is_valid:
                claimed_norm = self._normalize(question.correct_answer)
                
                # Case 1: solver explicitly says "claimed_answer_is_correct: true" but is_valid: false
                if validation.claimed_answer_is_correct is True:
                    print(f"  OVERRIDE: Solver said is_valid=false but claimed_answer_is_correct=true. Accepting question.")
                    return True
                
                # Case 2: corrected_answer matches the original claimed answer
                if validation.corrected_answer:
                    corrected_norm = self._normalize(validation.corrected_answer)
                    if corrected_norm == claimed_norm:
                        print(f"  OVERRIDE: Solver corrected_answer '{validation.corrected_answer}' matches claimed answer. Accepting question.")
                        return True
                
                # Case 3: computed_answer matches the claimed answer
                if validation.computed_answer:
                    computed_norm = self._normalize(validation.computed_answer)
                    if computed_norm == claimed_norm:
                        print(f"  OVERRIDE: Solver computed_answer '{validation.computed_answer}' matches claimed answer. Accepting question.")
                        return True
                
                # Genuine rejection — try to correct
                print(f"AI SOLVER REJECTED {question.id}: {validation.reason[:200]}")
                
                # Try to CORRECT the question if solver provides a corrected answer
                if validation.corrected_answer:
                    corrected = validation.corrected_answer.strip()
                    print(f"  Solver says correct answer should be: {corrected}")
                    
                    # Check if the corrected answer matches any existing option
                    for i, opt in enumerate(question.options):
                        opt_norm = self._normalize(opt)
                        corrected_norm = self._normalize(corrected)
                        
                        if (opt.strip() == corrected or 
                            opt_norm == corrected_norm or
                            corrected_norm in opt_norm or 
                            opt_norm in corrected_norm):
                            # Found the corrected answer in options — fix in place
                            print(f"  CORRECTING: Answer updated from '{question.correct_answer}' to '{opt}' (option index {i})")
                            question.correct_answer = opt
                            question.correct_option_index = i
                            return True
                    
                    print(f"  Corrected answer '{corrected}' not found in any option — rejecting entirely")
                
                # Also try computed_answer as a last resort
                if validation.computed_answer and validation.computed_answer != validation.corrected_answer:
                    computed = validation.computed_answer.strip()
                    for i, opt in enumerate(question.options):
                        opt_norm = self._normalize(opt)
                        computed_norm = self._normalize(computed)
                        if (opt.strip() == computed or
                            opt_norm == computed_norm or
                            computed_norm in opt_norm or
                            opt_norm in computed_norm):
                            print(f"  CORRECTING via computed_answer: Answer updated to '{opt}' (option index {i})")
                            question.correct_answer = opt
                            question.correct_option_index = i
                            return True
                
                return False
                
            return True
            
        except Exception as e:
            print(f"AI Solver Error: {e}")
            return True  # Fail open - structural already passed

    def _build_solver_prompt(self, question: GeneratedQuestion) -> str:
        options_text = "\n".join([f"  {i+1}. {opt}" for i, opt in enumerate(question.options)])
        return f"""You are a math/science exam answer verifier. Independently solve the question and check the claimed answer.

QUESTION: {question.question_text}

OPTIONS:
{options_text}

CLAIMED CORRECT ANSWER: {question.correct_answer}

STEPS:
1. Solve the question step by step. Show key calculations.
2. State your computed answer.
3. Compare your computed answer to the claimed answer.
4. Check if your computed answer is among the options.

CRITICAL FORMATTING RULES:
- Do NOT use LaTeX notation (no backslashes like \frac, \sqrt, \text) in your JSON output.
- Use plain text math: write fractions as a/b, square roots as sqrt(), powers as x^2, etc.
- This prevents JSON parsing errors from backslash escapes.

Output ONLY this JSON (no extra text):
{{
  "is_valid": true/false,
  "computed_answer": "your computed answer in plain text (no LaTeX)",
  "claimed_answer_is_correct": true/false,
  "reason": "brief explanation in plain text (no LaTeX)",
  "corrected_answer": "EXACT text of correct option if claimed is wrong, else null"
}}

IMPORTANT: Set is_valid=true if and only if claimed_answer_is_correct=true AND the answer exists in options.
"""

    def _call_gemini_solver(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Gemini to verify a question's answer with robust JSON parsing."""
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Very low for deterministic math
                    response_mime_type="application/json"
                )
            )
            content = response.text.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            return self._parse_solver_json(content)
        except Exception as e:
            print(f"Validator Gemini Call Error: {e}")
            return None

    def _parse_solver_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse solver JSON with multiple fallback strategies for LaTeX escapes."""
        # Strategy 1: Direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Strategy 2: strict=False for control characters
        try:
            return json.JSONDecoder(strict=False).decode(content)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Fix invalid backslash escapes (LaTeX commands)
        cleaned = re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        fixed = re.sub(r'\\(?!["\\\\/{bfnrtu])', r'\\\\', cleaned)
        try:
            return json.JSONDecoder(strict=False).decode(fixed)
        except json.JSONDecodeError:
            pass

        # Strategy 4: Aggressively double ALL single backslashes
        sanitized = self._sanitize_backslashes(cleaned)
        try:
            return json.JSONDecoder(strict=False).decode(sanitized)
        except json.JSONDecodeError:
            pass

        # Strategy 5: Extract outermost JSON object
        try:
            brace_start = cleaned.find('{')
            brace_end = cleaned.rfind('}')
            if brace_start != -1 and brace_end > brace_start:
                json_substr = cleaned[brace_start:brace_end + 1]
                fixed_substr = re.sub(r'\\(?!["\\\\/{bfnrtu])', r'\\\\', json_substr)
                return json.JSONDecoder(strict=False).decode(fixed_substr)
        except (json.JSONDecodeError, ValueError):
            pass

        print(f"Validator JSON parse failed after all strategies")
        return None

    def _sanitize_backslashes(self, text: str) -> str:
        """Double all single backslashes for JSON parsing."""
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
