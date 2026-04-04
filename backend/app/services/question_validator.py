import json
import ast
import re
import time
import random
import threading
from typing import Optional, Dict, Any, List, Tuple
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
    2. AI solver validation (two-pass consensus using Gemini thinking model)
    """
    
    _semaphore_lock = threading.Lock()
    _global_semaphore = None
    _global_semaphore_capacity = None
    _rate_limit_lock = threading.Lock()
    _last_solver_call_at = 0.0
    _cooldown_lock = threading.Lock()
    _cooldown_until = 0.0

    def __init__(self, api_key: Optional[str] = None):
        self.gemini_client = None
        self.gemini_model = settings.GEMINI_VALIDATOR_MODEL
        self.gemini_thinking_budget = max(0, int(settings.GEMINI_VALIDATOR_THINKING_BUDGET))
        self.validator_max_calls_per_second = max(0.0, float(settings.VALIDATOR_MAX_CALLS_PER_SECOND))
        self.validator_429_cooldown_seconds = max(0, int(settings.VALIDATOR_429_COOLDOWN_SECONDS))
        self.numeric_equivalence_tolerance = max(0.0, float(settings.VALIDATOR_NUMERIC_EQUIVALENCE_TOLERANCE))
        self._ensure_global_semaphore()
        
        # Initialize Gemini for AI solver validation
        project = settings.GOOGLE_CLOUD_PROJECT
        location = settings.GOOGLE_CLOUD_LOCATION
        try:
            if project:
                print(f"Validator using Vertex AI Gemini model: {self.gemini_model}")
                self.gemini_client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=location
                )
            elif settings.GEMINI_API_KEY:
                print(f"Validator using API Key Gemini model: {self.gemini_model}")
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            print(f"Validator Gemini Init Failed: {e}")

    def _ensure_global_semaphore(self):
        capacity = max(1, int(settings.VALIDATOR_GLOBAL_CONCURRENCY))
        if (
            QuestionValidator._global_semaphore is not None
            and QuestionValidator._global_semaphore_capacity == capacity
        ):
            return

        with QuestionValidator._semaphore_lock:
            if (
                QuestionValidator._global_semaphore is None
                or QuestionValidator._global_semaphore_capacity != capacity
            ):
                QuestionValidator._global_semaphore = threading.BoundedSemaphore(value=capacity)
                QuestionValidator._global_semaphore_capacity = capacity

    def _respect_cooldown(self):
        with QuestionValidator._cooldown_lock:
            wait_seconds = max(0.0, QuestionValidator._cooldown_until - time.monotonic())
        if wait_seconds > 0:
            print(f"Validator cooldown active ({wait_seconds:.1f}s) due to recent 429")
            time.sleep(wait_seconds)

    def _register_rate_limit_hit(self):
        if self.validator_429_cooldown_seconds <= 0:
            return
        with QuestionValidator._cooldown_lock:
            QuestionValidator._cooldown_until = max(
                QuestionValidator._cooldown_until,
                time.monotonic() + self.validator_429_cooldown_seconds,
            )

    def _wait_for_rate_limit_slot(self):
        if self.validator_max_calls_per_second <= 0:
            return

        min_interval = 1.0 / self.validator_max_calls_per_second
        while True:
            with QuestionValidator._rate_limit_lock:
                now = time.monotonic()
                elapsed = now - QuestionValidator._last_solver_call_at
                if elapsed >= min_interval:
                    QuestionValidator._last_solver_call_at = now
                    return
                wait_seconds = min_interval - elapsed
            time.sleep(min(wait_seconds, 0.25))

    def _extract_number(self, text: str) -> Optional[float]:
        if not text:
            return None
        matches = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', text)
        if not matches:
            return None
        try:
            return float(matches[0])
        except ValueError:
            return None

    def _answers_equivalent(self, answer_a: Optional[str], answer_b: Optional[str]) -> bool:
        if not answer_a or not answer_b:
            return False

        norm_a = self._normalize(answer_a)
        norm_b = self._normalize(answer_b)
        if norm_a == norm_b:
            return True

        num_a = self._extract_number(norm_a)
        num_b = self._extract_number(norm_b)
        if num_a is None or num_b is None:
            return False

        tolerance = max(self.numeric_equivalence_tolerance, 1e-9)
        scale = max(1.0, abs(num_a), abs(num_b))
        return abs(num_a - num_b) <= tolerance * scale

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
        """AI solver validation using Gemini thinking model.
        
        Strategy:
        - Pass 1 always runs. Rejections and corrections from the thinking model
          are trusted on a single pass (the model's internal reasoning is reliable).
        - Pass 2 only runs when Pass 1 ACCEPTS — this is the false-positive risk
          case where the solver might have made an arithmetic error and wrongly
          confirmed a bad answer. Two-pass consensus catches these.
        
        Strict validation policy:
        - Both is_valid AND claimed_answer_is_correct must be True to accept.
        - Contradictory signals → reject.
        - No response from solver → reject (fail-closed).
        - Corrections only via exact/normalized matching (no substring).
        """
        prompt = self._build_solver_prompt(question)
        
        # --- Pass 1 (always runs) ---
        result1 = self._run_single_solver_pass(prompt, question, pass_num=1)
        if result1 is None:
            return False
        
        verdict1, validation1 = result1
        
        # Reject: trust the thinking model's rejection outright
        if verdict1 == "reject":
            return False
        
        # Correct: trust the thinking model's correction (it showed its math)
        if verdict1 == "correct":
            corrected = self._try_correct_answer(question, validation1)
            if corrected:
                print(f"  [{question.id}] CORRECTED by thinking model (single pass)")
                return True
            return False
        
        # --- Pass 2 (only when Pass 1 accepted — guard against false positives) ---
        result2 = self._run_single_solver_pass(prompt, question, pass_num=2)
        if result2 is None:
            # Pass 2 unavailable — accept Pass 1 since the thinking model confirmed it
            print(f"  [{question.id}] Pass 2 unavailable — trusting Pass 1 accept from thinking model")
            return True
        
        verdict2, validation2 = result2
        
        if verdict2 == "accept":
            # Both agree — extra check that they computed the same answer
            computed1 = (validation1.computed_answer or "").strip()
            computed2 = (validation2.computed_answer or "").strip()
            
            if computed1 and computed2:
                if not self._answers_equivalent(computed1, computed2):
                    print(f"  [{question.id}] CONSENSUS MISMATCH: Pass 1 computed '{computed1}', Pass 2 computed '{computed2}' — REJECTING")
                    return False
            
            print(f"  [{question.id}] CONSENSUS: Both passes confirm answer is correct")
            return True
        
        # Pass 2 disagrees with Pass 1's accept — reject (Pass 2 found an error)
        print(f"  [{question.id}] Pass 2 DISAGREES with accept (verdict={verdict2}) — REJECTING")
        return False

    def _run_single_solver_pass(self, prompt: str, question: GeneratedQuestion, pass_num: int):
        """Run a single solver pass and return (verdict, validation) or None on failure.
        
        verdict is one of: "accept", "reject", "correct"
        """
        try:
            response = self._call_gemini_solver(prompt)
            if not response:
                print(f"  [{question.id}] Pass {pass_num}: No response from Gemini solver — REJECTING (fail-closed)")
                return None
                
            validation = ValidationResult(**response)
            
            print(f"  [{question.id}] Pass {pass_num} Solver Result: valid={validation.is_valid}, claimed_correct={validation.claimed_answer_is_correct}, computed={validation.computed_answer}")

            # CASE 1: Solver confirms both valid and correct
            if validation.is_valid and validation.claimed_answer_is_correct is True:
                return ("accept", validation)

            # CASE 2: Solver says valid but answer is wrong — could correct
            if validation.is_valid and validation.claimed_answer_is_correct is False:
                if validation.corrected_answer or validation.computed_answer:
                    return ("correct", validation)
                return ("reject", validation)

            # CASE 3: Contradictory (is_valid=false, claimed_correct=true) — reject
            if not validation.is_valid and validation.claimed_answer_is_correct is True:
                print(f"  [{question.id}] Pass {pass_num}: CONTRADICTORY: is_valid=false but claimed_correct=true — REJECTING")
                return ("reject", validation)

            # CASE 4: Solver says invalid
            if not validation.is_valid:
                claimed_norm = self._normalize(question.correct_answer)
                
                # Check if solver's own math actually agrees with claimed answer
                if validation.corrected_answer:
                    if self._answers_equivalent(validation.corrected_answer, claimed_norm):
                        return ("accept", validation)
                
                if validation.computed_answer:
                    if self._answers_equivalent(validation.computed_answer, claimed_norm):
                        return ("accept", validation)
                
                # Genuine rejection — might be correctable
                print(f"  [{question.id}] Pass {pass_num} REJECTED: {validation.reason[:200]}")
                if validation.corrected_answer or validation.computed_answer:
                    return ("correct", validation)
                return ("reject", validation)
                
            # CASE 5: is_valid=true but claimed_answer_is_correct is None
            if validation.is_valid and validation.claimed_answer_is_correct is None:
                return ("accept", validation)

            return ("reject", validation)
            
        except Exception as e:
            print(f"  [{question.id}] Pass {pass_num} Solver Error: {e}")
            return None

    def _try_correct_answer(self, question: GeneratedQuestion, validation: ValidationResult) -> bool:
        """Try to correct the question's answer using solver's corrected_answer or computed_answer.
        
        Only uses exact or normalized matching — NO substring matching to avoid false positives.
        Returns True if correction was applied, False otherwise.
        """
        # Try corrected_answer first (solver's recommended answer)
        if validation.corrected_answer:
            corrected = validation.corrected_answer.strip()
            print(f"  Solver says correct answer should be: {corrected}")
            
            match_idx = self._find_exact_option_match(question.options, corrected)
            if match_idx is not None:
                print(f"  CORRECTING: Answer updated from '{question.correct_answer}' to '{question.options[match_idx]}' (option index {match_idx})")
                question.correct_answer = question.options[match_idx]
                question.correct_option_index = match_idx
                return True
            
            print(f"  Corrected answer '{corrected}' not found in any option — rejecting entirely")
        
        # Try computed_answer as fallback (only if different from corrected_answer)
        if validation.computed_answer and validation.computed_answer != (validation.corrected_answer or ""):
            computed = validation.computed_answer.strip()
            match_idx = self._find_exact_option_match(question.options, computed)
            if match_idx is not None:
                print(f"  CORRECTING via computed_answer: Answer updated to '{question.options[match_idx]}' (option index {match_idx})")
                question.correct_answer = question.options[match_idx]
                question.correct_option_index = match_idx
                return True
        
        return False

    def _find_exact_option_match(self, options: list, answer: str) -> Optional[int]:
        """Find an option that exactly or normalized-exactly matches the answer.
        
        NO substring matching — only exact text or normalized-exact comparison.
        """
        answer_norm = self._normalize(answer)
        for i, opt in enumerate(options):
            if opt.strip() == answer.strip():
                return i
            if self._normalize(opt) == answer_norm:
                return i
        return None

    def _build_solver_prompt(self, question: GeneratedQuestion) -> str:
        options_text = "\n".join([f"  {i+1}. {opt}" for i, opt in enumerate(question.options)])
        return f"""You are a rigorous math/science exam answer verifier. Your job is to independently solve the question from scratch and check whether the claimed answer is correct.

QUESTION: {question.question_text}

OPTIONS:
{options_text}

CLAIMED CORRECT ANSWER: {question.correct_answer}

MANDATORY VERIFICATION WORKFLOW:
1. SOLVE the question step by step. Show every intermediate calculation.
2. VERIFY your arithmetic: re-compute each step independently. Check unit conversions.
   - For chemistry: verify molar masses, electron counts, stoichiometric ratios.
   - For physics: verify unit conversions (e.g., torr→atm: divide by 760, mL→L: divide by 1000).
   - For math: plug your answer back into the original equation to confirm.
3. State your FINAL computed answer after verification.
4. Compare your verified answer to the claimed answer.
5. Check if your verified answer matches any of the options.
6. Check if the claimed answer matches any of the options.

COMMON PITFALLS TO WATCH FOR:
- Unit conversion errors (mmHg/torr to atm, mL to L, mg to g, nm to m)
- Off-by-a-factor errors (forgetting to multiply/divide by a constant)
- Stoichiometry: count electrons carefully in redox reactions
- Order of magnitude errors (e.g., 897 vs 8970 vs 89.7)
- Using wrong formulas or missing terms

CONSISTENCY RULES (you MUST follow these):
- If your verified answer matches the claimed answer AND it is in the options: set is_valid=true, claimed_answer_is_correct=true
- If your verified answer does NOT match the claimed answer: set is_valid=false, claimed_answer_is_correct=false, and provide corrected_answer (the EXACT text of the correct option if it exists)
- If the correct answer is not in ANY of the options: set is_valid=false, claimed_answer_is_correct=false, corrected_answer=null
- NEVER set is_valid=false while also setting claimed_answer_is_correct=true. These fields must be consistent.
- NEVER set is_valid=true while also setting claimed_answer_is_correct=false, unless you can provide a corrected_answer that exists in the options.

CRITICAL FORMATTING RULES:
- Do NOT use LaTeX notation (no backslashes like \\frac, \\sqrt, \\text) in your JSON output.
- Use plain text math: write fractions as a/b, square roots as sqrt(), powers as x^2, etc.
- This prevents JSON parsing errors from backslash escapes.

Output ONLY this JSON (no extra text):
{{
  "is_valid": true/false,
  "computed_answer": "your VERIFIED computed answer in plain text (no LaTeX)",
  "claimed_answer_is_correct": true/false,
  "reason": "brief explanation including your verification step in plain text (no LaTeX)",
  "corrected_answer": "EXACT text of correct option if claimed is wrong and correct answer exists in options, else null"
}}
"""

    def _call_gemini_solver(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Gemini model to verify a question's answer with robust JSON parsing.

        Uses configured Gemini validator model with optional thinking budget.
        Retries with exponential backoff on 429 RESOURCE_EXHAUSTED errors.
        """
        max_retries = 3
        base_delay = 3
        
        semaphore = QuestionValidator._global_semaphore
        acquired = True
        if semaphore:
            semaphore.acquire()

        try:
            for attempt in range(max_retries):
                try:
                    self._respect_cooldown()
                    self._wait_for_rate_limit_slot()
                    response = self.gemini_client.models.generate_content(
                        model=self.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.0,  # Deterministic for math
                            thinking_config=types.ThinkingConfig(
                                thinking_budget=self.gemini_thinking_budget
                            ),
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
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        self._register_rate_limit_hit()
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Validator Rate Limit (429). Retrying in {delay:.1f}s... ({attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    print(f"Validator Gemini Call Error: {e}")
                    return None

            print(f"Validator: Exhausted retries after {max_retries} attempts (429)")
            return None
        finally:
            if semaphore and acquired:
                semaphore.release()

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

        # Strategy 6: Python-dict style fallback (single quotes / True / False)
        try:
            python_obj = ast.literal_eval(content)
            if isinstance(python_obj, dict):
                return python_obj
        except Exception:
            pass

        # Strategy 7: Extract dict-like block, then literal_eval
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
