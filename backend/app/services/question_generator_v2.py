"""
Question Generator V2 - Deterministic Question Generation Pipeline

Implements the proper workflow:
- Phase 2: Blueprint → Variable Sampling → Answer Computation (code only, NO AI)
- Phase 3: Blueprint-driven distractors with formula-based errors
- Phase 4: Validation gate before output

AI is ONLY used for question text phrasing (optional), NEVER for:
- Variable selection
- Answer computation
- Option generation
"""

import random
import math
import re
import uuid
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

try:
    from groq import Groq
except ImportError:
    Groq = None

from app.models.blueprint import (
    Blueprint,
    GeneratedQuestion,
    DifficultyLevel,
    Constraints,
    AnswerType,
)
from app.services.blueprint_loader import get_blueprint_loader, BlueprintLoader
from app.core.config import settings
from app.services.ai_question_generator import AIQuestionGenerator
from app.services.question_validator import QuestionValidator


# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_GENERATION_RETRIES = 5  # Max attempts before discarding a blueprint
ANSWER_PRECISION = 2  # Decimal places for numeric answers


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationResult:
    """Result of question validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


# =============================================================================
# QUESTION GENERATOR V2
# =============================================================================

class QuestionGeneratorV2:
    """
    Hybrid Question Generator:
    1. Static Blueprints -> Instant generation (Deterministic)
    2. Dynamic Blueprints -> AI-Driven Generation (LLM + Validation)
    """

    def __init__(self, loader: Optional[BlueprintLoader] = None):
        self.loader = loader or get_blueprint_loader()
        self.ai_generator = AIQuestionGenerator()
        self.validator = QuestionValidator()
        self.llm_model = "llama-3.1-8b-instant" # Keep for phrasing if needed

    # =========================================================================
    # PHASE 2: DETERMINISTIC QUESTION CORE
    # =========================================================================

    def generate_from_blueprint(
        self,
        blueprint: Blueprint,
        seed: Optional[int] = None,
        use_ai_phrasing: bool = False,
        max_retries: int = MAX_GENERATION_RETRIES,
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a question from a blueprint.
        
        Route:
        - STATIC Blueprint (no variables): Use purely deterministic generation (fast).
        - DYNAMIC Blueprint (has variables): Use AI Generator + Validator (smart).
        """
        if seed is not None:
            random.seed(seed)

        # 1. OPTIMIZATION: If blueprint is static, don't waste AI tokens
        if not blueprint.variables:
            return self._generate_static_question(blueprint)

        # 2. AI GENERATION LOOP
        for attempt in range(max_retries):
            try:
                # A. Generate
                question = self.ai_generator.generate_question(blueprint)
                if not question:
                    print(f"AI Generation failed for {blueprint.id}, attempt {attempt+1}")
                    continue
                
                print(f"Generated Question Candidate: {question.question_text[:50]}...")

                # B. Validate
                is_valid = self.validator.validate_question(question, blueprint)
                print(f"Validation Status: {is_valid}")
                
                if is_valid:
                    return question
                
                print(f"Validation failed for {blueprint.id}, retrying...")

            except Exception as e:
                print(f"Error generating question for {blueprint.id}: {e}")
                import traceback
                with open("gen_error.log", "w") as f:
                    traceback.print_exc(file=f)
                continue
        
        print(f"Failed to generate valid question for {blueprint.id} after {max_retries} retries.")
        return None

    def _generate_static_question(self, blueprint: Blueprint) -> Optional[GeneratedQuestion]:
        """Generate a question from a static blueprint (no variables)."""
        # Determine the correct answer
        # For static blueprints, the first option is assumed to be correct before shuffling
        if blueprint.answer_options and len(blueprint.answer_options) > 0:
            correct_option_text = blueprint.answer_options[0]
        else:
            correct_option_text = "Correct Answer"
        
        # Get options
        options = []
        if blueprint.answer_options:
            options = list(blueprint.answer_options)
        
        # Ensure correct answer is in options
        if correct_option_text and correct_option_text not in options:
            options.append(correct_option_text)
            
        # Shuffle
        random.shuffle(options)
        
        # Find index
        try:
            correct_idx = options.index(correct_option_text)
        except ValueError:
            correct_idx = 0

        return GeneratedQuestion(
            id=str(uuid.uuid4()),
            blueprint_id=blueprint.id,
            question_text=blueprint.template_variants[0] if blueprint.template_variants else blueprint.template or "Question Text Missing",
            options=options,
            correct_answer=correct_option_text,
            correct_option_index=correct_idx,
            solution="Static question - see concept tags.",
            variables_used={},
            difficulty_level=blueprint.difficulty_level or DifficultyLevel.MODERATE,
            subject=blueprint.subject,
            chapter=blueprint.chapter,
            concept=blueprint.concept,
            tags=blueprint.tags or [],
            expected_time_sec=blueprint.constraints.expected_time_sec if blueprint.constraints else 60,
            generated_at=datetime.now(timezone.utc),
        )

    def _sample_variables(self, blueprint: Blueprint) -> Dict[str, Any]:
        """
        Sample variable values within blueprint constraints.
        
        This is pure code - NO AI involvement.
        """
        variables = {}
        
        if not blueprint.variables:
            return variables

        for var_name, var_config in blueprint.variables.items():
            if isinstance(var_config, dict):
                var_type = var_config.get('type', 'integer')
                
                if var_type == 'integer':
                    range_vals = var_config.get('range', [1, 10])
                    step = var_config.get('step', 1)
                    exclude = var_config.get('exclude', [])
                    
                    # Generate all valid values
                    values = [
                        v for v in range(range_vals[0], range_vals[1] + 1, step)
                        if v not in exclude
                    ]
                    
                    if values:
                        variables[var_name] = random.choice(values)
                    else:
                        variables[var_name] = range_vals[0]
                
                elif var_type == 'float':
                    range_vals = var_config.get('range', [1.0, 10.0])
                    precision = var_config.get('precision', ANSWER_PRECISION)
                    value = random.uniform(range_vals[0], range_vals[1])
                    variables[var_name] = round(value, precision)
                
                elif var_type == 'choice':
                    values = var_config.get('values', [])
                    if values:
                        choice = random.choice(values)
                        if isinstance(choice, dict):
                            # Unpack dict choice
                            variables[var_name] = choice
                            for k, v in choice.items():
                                variables[k] = v
                        else:
                            variables[var_name] = choice
                
                elif var_type == 'integer_list':
                    range_vals = var_config.get('range', [1, 10])
                    length = var_config.get('length', 3)
                    variables[var_name] = [
                        random.randint(range_vals[0], range_vals[1])
                        for _ in range(length)
                    ]
            else:
                # Simple value
                variables[var_name] = var_config

        # Compute derived variables for common patterns
        variables = self._compute_derived_variables(variables)

        return variables

    def _compute_derived_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute common derived variables from base variables.
        E.g., a_plus_d = a + d for AP sequences.
        """
        derived = dict(variables)
        
        # AP/GP sequence patterns
        if 'a' in variables and 'd' in variables:
            a, d = variables['a'], variables['d']
            if isinstance(a, (int, float)) and isinstance(d, (int, float)):
                derived['a_plus_d'] = a + d
                derived['a_plus_2d'] = a + 2 * d
                derived['a_plus_3d'] = a + 3 * d
                derived['a_minus_d'] = a - d
        
        # Common ratio patterns for GP
        if 'a' in variables and 'r' in variables:
            a, r = variables['a'], variables['r']
            if isinstance(a, (int, float)) and isinstance(r, (int, float)):
                derived['ar'] = a * r
                derived['ar2'] = a * r * r
                derived['ar3'] = a * r * r * r
        
        # Quadratic patterns
        if 'a' in variables and 'b' in variables and 'c' in variables:
            a, b, c = variables['a'], variables['b'], variables['c']
            if all(isinstance(x, (int, float)) for x in [a, b, c]):
                # Discriminant
                derived['discriminant'] = b * b - 4 * a * c
                # Vertex x-coordinate
                if a != 0:
                    derived['vertex_x'] = -b / (2 * a)
        
        return derived

    def _compute_answer(
        self,
        blueprint: Blueprint,
        variables: Dict[str, Any]
    ) -> Tuple[Any, str]:
        """
        Compute answer using code evaluation.
        
        ❌ AI must NOT compute answers - this is pure code.
        
        Returns:
            Tuple of (raw_answer, display_string)
        """
        # Handle function expressions like f(x) = x² + 2x, find f(2)
        if 'expr' in variables and 'val' in variables:
            return self._evaluate_function_expression(variables, blueprint)
        
        # No formula - check for pre-defined answer
        if not blueprint.formula:
            if 'answer' in variables:
                ans = variables['answer']
                return ans, str(ans)
            return None, "N/A"

        try:
            # Build evaluation context with math functions
            eval_context = {
                'math': math,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'pi': math.pi,
                'e': math.e,
                'abs': abs,
                'sum': sum,
                'min': min,
                'max': max,
                'round': round,
                'pow': pow,
                **variables
            }

            formula = blueprint.formula
            
            # Handle "answer = expression" format
            if '=' in formula and not any(op in formula for op in ['==', '<=', '>=']):
                parts = formula.split('=')
                if len(parts) == 2:
                    formula = parts[1].strip()

            # Clean formula for evaluation
            # Only strip leading/trailing whitespace (don't remove parenthetical content - that breaks math!)
            formula = formula.strip()
            
            # Convert mathematical notation to Python syntax
            formula = self._normalize_formula(formula)

            # Evaluate
            answer = eval(formula, {"__builtins__": {}}, eval_context)

            # Format display
            display = self._format_answer_display(answer, blueprint)
            
            return answer, display

        except Exception as e:
            # Don't print for every failure - will use fallback
            return None, "Error"

    def _fallback_answer(
        self,
        blueprint: Blueprint,
        variables: Dict[str, Any]
    ) -> Tuple[Any, str]:
        """
        Fallback answer generation when formula evaluation fails.
        
        STRICT POLICY: Only use pre-defined answers, NEVER guess.
        If no valid answer exists, return None to trigger retry/discard.
        
        Strategies:
        1. Use answer_options[0] if available (pre-validated)
        2. Use 'answer' from variables if present (blueprint-defined)
        
        ❌ REMOVED: Never generate "plausible" answers from variable averaging
           This was causing wrong answers that looked reasonable.
        """
        # Strategy 1: Pre-defined answer options (from blueprint)
        if blueprint.answer_options and len(blueprint.answer_options) > 0:
            answer = blueprint.answer_options[0]
            return answer, str(answer)
        
        # Strategy 2: Answer in variables (blueprint-defined)
        if 'answer' in variables:
            ans = variables['answer']
            return ans, str(ans)
        
        # NO FALLBACK - If formula failed and no pre-defined answer exists,
        # this blueprint is broken and should be discarded
        print(f"WARNING: Blueprint {blueprint.id} has no valid answer computation")
        return None, "N/A"

    def _evaluate_function_expression(
        self,
        variables: Dict[str, Any],
        blueprint: Blueprint
    ) -> Tuple[Any, str]:
        """Evaluate f(x) = expression at x = value."""
        expr = variables.get('expr', '')
        val = variables.get('val', 0)

        try:
            # Convert to Python expression using normalize_formula
            py_expr = self._normalize_formula(expr)
            
            # Additional x-specific patterns
            py_expr = re.sub(r'x\*\*2', 'x**2', py_expr)
            py_expr = re.sub(r'x\*\*3', 'x**3', py_expr)

            eval_context = {
                'x': val,
                'math': math,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'abs': abs,
                'pi': math.pi,
            }

            answer = eval(py_expr, {"__builtins__": {}}, eval_context)
            display = self._format_answer_display(answer, blueprint)
            
            return answer, display

        except Exception as e:
            return None, "Error"

    def _format_answer_display(self, answer: Any, blueprint: Blueprint) -> str:
        """Format answer for display with units."""
        if isinstance(answer, float):
            if answer == int(answer):
                display = str(int(answer))
            else:
                display = f"{answer:.{ANSWER_PRECISION}f}"
        else:
            display = str(answer)

        # Add unit if specified
        if blueprint.answer_unit and blueprint.answer_unit != "dimensionless":
            display = f"{display} {blueprint.answer_unit}"

        return display

    def _normalize_formula(self, formula: str) -> str:
        """
        Convert mathematical notation to Python-evaluable syntax.
        
        Handles:
        - Superscript numbers (², ³, ⁴, etc.) → **2, **3, **4
        - Subscript numbers (₀, ₁, ₂, etc.) → 0, 1, 2
        - Multiplication sign (×) → *
        - Division sign (÷) → /
        - Greek letters (π, θ, etc.)
        - Common physics notation (ε₀, μ₀, etc.)
        """
        result = formula
        
        # Superscripts to powers
        superscripts = {
            '⁰': '**0', '¹': '**1', '²': '**2', '³': '**3', '⁴': '**4',
            '⁵': '**5', '⁶': '**6', '⁷': '**7', '⁸': '**8', '⁹': '**9'
        }
        for sup, rep in superscripts.items():
            result = result.replace(sup, rep)
        
        # Subscripts to regular numbers (for variable names like R₁ → R1)
        subscripts = {
            '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
            '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9'
        }
        for sub, rep in subscripts.items():
            result = result.replace(sub, rep)
        
        # Math operators
        result = result.replace('×', '*')
        result = result.replace('÷', '/')
        result = result.replace('−', '-')  # Unicode minus
        
        # Greek letters to values/names
        greek_replacements = {
            'π': 'pi',
            'θ': 'theta',
            'φ': 'phi',
            'ω': 'omega',
            'α': 'alpha',
            'β': 'beta',
            'γ': 'gamma',
            'λ': 'lambda_val',
            'μ': 'mu',
            'ε': 'epsilon',
            'σ': 'sigma',
            'ρ': 'rho',
        }
        for greek, name in greek_replacements.items():
            result = result.replace(greek, name)
        
        # Common physics constants (subscripted)
        result = re.sub(r'epsilon0|ε0', '8.854e-12', result)  # ε₀
        result = re.sub(r'mu0|μ0', '1.257e-6', result)  # μ₀
        
        # Fix implicit multiplication: "2x" → "2*x", "3a" → "3*a"
        result = re.sub(r'(\d)([a-zA-Z_])', r'\1*\2', result)
        
        # Fix implicit multiplication: ")(" → ")*("
        result = result.replace(')(', ')*(')
        
        # Fix implicit multiplication: ")a" → ")*a" (closing paren followed by variable)
        result = re.sub(r'\)([a-zA-Z_])', r')*\1', result)
        
        # Convert square brackets to parentheses (math grouping, not Python lists)
        # Also handle implicit multiplication: )[... → )*(... and ](... → )*(
        result = result.replace(')[', ')*(')
        result = result.replace('][', ')*(')
        result = result.replace('[', '(')
        result = result.replace(']', ')')
        
        # Handle sqrt notation
        result = re.sub(r'√\(([^)]+)\)', r'sqrt(\1)', result)
        result = re.sub(r'√(\d+)', r'sqrt(\1)', result)
        
        return result

    def _validate_answer(self, answer: Any, constraints: Constraints) -> bool:
        """
        Validate answer against blueprint constraints.
        
        If this fails, the generation will retry with new variables.
        """
        if answer is None:
            return False

        # Ensure integer answer
        if constraints.ensure_integer_answer:
            if isinstance(answer, float) and answer != int(answer):
                return False

        # Check answer range
        if constraints.answer_range:
            try:
                ans_num = float(answer) if not isinstance(answer, (int, float)) else answer
                min_val, max_val = constraints.answer_range
                if not (min_val <= ans_num <= max_val):
                    return False
            except (ValueError, TypeError):
                pass

        return True

    # =========================================================================
    # PHASE 2 CONT: QUESTION TEXT GENERATION
    # =========================================================================

    def _generate_question_text(
        self,
        blueprint: Blueprint,
        variables: Dict[str, Any],
        use_ai_phrasing: bool = False
    ) -> str:
        """
        Generate question text from template.
        
        AI (if used) only does:
        ✔ phrasing
        ✔ grammar
        ✔ formatting
        
        ❌ no logic
        ❌ no value choice
        ❌ no answer
        """
        # Select template
        template = random.choice(blueprint.template_variants) if blueprint.template_variants else blueprint.template or ""
        
        # Fill with variable values (deterministic)
        question_text = self._fill_template(template, variables)
        
        # Optional: AI phrasing improvement
        if use_ai_phrasing and self.llm_client:
            improved = self._improve_phrasing_with_ai(question_text, blueprint)
            if improved:
                question_text = improved

        return question_text

    def _fill_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Fill template with variable values."""
        result = template

        # Sort by length (longest first) to avoid partial replacements
        sorted_vars = sorted(variables.keys(), key=len, reverse=True)

        for var_name in sorted_vars:
            value = variables[var_name]
            if isinstance(value, dict):
                continue  # Skip dict values

            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)

            result = result.replace(f"{{{var_name}}}", value_str)

        # Fix ordinal numbers: "3th" -> "3rd", "2th" -> "2nd", etc.
        result = self._fix_ordinals(result)

        return result

    def _fix_ordinals(self, text: str) -> str:
        """Fix incorrect ordinal suffixes like '3th' -> '3rd'."""
        def ordinal_replace(match):
            num = int(match.group(1))
            correct_suffix = self._get_ordinal_suffix(num)
            return f"{num}{correct_suffix}"
        
        # Match patterns like "3th", "2th", "1th", "21th" etc.
        pattern = r'(\d+)(th|st|nd|rd)\b'
        result = re.sub(pattern, ordinal_replace, text)
        return result

    def _get_ordinal_suffix(self, n: int) -> str:
        """Get the correct ordinal suffix for a number."""
        if 11 <= n % 100 <= 13:
            return 'th'
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

    def _improve_phrasing_with_ai(
        self,
        question_text: str,
        blueprint: Blueprint
    ) -> Optional[str]:
        """
        Use AI ONLY for phrasing improvement.
        
        The AI receives the complete question with values already filled in.
        It can ONLY improve grammar and clarity, NOT change any values or logic.
        """
        if not self.llm_client:
            return None

        try:
            prompt = f"""Improve the phrasing of this exam question for clarity and proper grammar.
            
RULES:
- Do NOT change any numerical values
- Do NOT change the mathematical expressions
- Do NOT change the meaning or logic
- Only improve grammar, clarity, and formatting
- Keep it concise (max 2-3 sentences)
- Return ONLY the improved question text, nothing else

Original question:
{question_text}

Improved question:"""

            completion = self.llm_client.chat.completions.create(
                model=self.llm_model,
                temperature=0.1,  # Low temperature for minimal changes
                max_tokens=200,
                messages=[
                    {"role": "system", "content": "You are a grammar expert. Only fix phrasing, never change values or logic."},
                    {"role": "user", "content": prompt},
                ],
            )

            improved = completion.choices[0].message.content.strip()
            
            # Validate that numbers weren't changed (safety check)
            original_numbers = set(re.findall(r'\d+\.?\d*', question_text))
            improved_numbers = set(re.findall(r'\d+\.?\d*', improved))
            
            if original_numbers != improved_numbers:
                # AI changed numbers - reject and use original
                return None

            return improved

        except Exception as e:
            print(f"AI phrasing failed: {e}")
            return None

    # =========================================================================
    # PHASE 3: OPTION (MCQ) GENERATION
    # =========================================================================

    def _generate_options(
        self,
        blueprint: Blueprint,
        answer: Any,
        answer_display: str,
        variables: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        """
        Generate MCQ options based on blueprint's answer_type.
        
        Type-aware dispatch:
        - NUMERICAL: Compute distractors from formulas/common errors
        - CATEGORICAL: Use pre-defined answer_options (REQUIRED)
        - COORDINATE: Format as (x, y) pairs
        - EXPRESSION: Symbolic options
        - BOOLEAN: True/False type
        
        ❌ Never random numbers
        ❌ Never AI-invented options
        ❌ Never placeholder text
        
        Returns:
            Tuple of (options_list, correct_index)
        """
        # Normalize answer_type (handle both enum and string)
        answer_type = blueprint.answer_type
        if isinstance(answer_type, str):
            answer_type = answer_type.lower()
        else:
            answer_type = answer_type.value if hasattr(answer_type, 'value') else str(answer_type).lower()
        
        # CATEGORICAL / BOOLEAN: Must use answer_options
        if answer_type in ['categorical', 'boolean']:
            return self._generate_categorical_options(blueprint, answer_display, variables)
        
        # COORDINATE: Format as coordinate pairs
        if answer_type == 'coordinate':
            return self._generate_coordinate_options(blueprint, answer, answer_display, variables)
        
        # EXPRESSION: Symbolic options
        if answer_type == 'expression':
            return self._generate_expression_options(blueprint, answer_display, variables)
        
        # NUMERICAL (default): Compute distractors
        return self._generate_numerical_options(blueprint, answer, answer_display, variables)

    def _generate_numerical_options(
        self,
        blueprint: Blueprint,
        answer: Any,
        answer_display: str,
        variables: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        """Generate options for numerical answer type."""
        unit = blueprint.answer_unit if blueprint.answer_unit != "dimensionless" else ""
        
        # If blueprint has pre-defined answer_options, use them
        if blueprint.answer_options and len(blueprint.answer_options) >= 4:
            options = list(blueprint.answer_options[:4])
            random.shuffle(options)
            correct_idx = self._find_correct_index(options, answer_display, answer)
            return options, correct_idx

        # Fallback for non-numeric answers
        if answer is None or (isinstance(answer, str) and not self._is_numeric(answer)):
            return self._generate_categorical_options(blueprint, answer_display, variables)

        # Numeric answer - generate distractors
        try:
            answer_num = float(answer) if not isinstance(answer, (int, float)) else answer
        except (ValueError, TypeError):
            # Can't parse as number - mark as broken
            return [answer_display, "__PLACEHOLDER_1__", "__PLACEHOLDER_2__", "__PLACEHOLDER_3__"], 0

        distractors = self._generate_distractors(blueprint, answer_num, variables)
        
        # Format all options
        all_values = [answer_num] + distractors
        
        # Apply same formatting/rounding
        if isinstance(answer_num, float) and answer_num != int(answer_num):
            all_values = [round(v, ANSWER_PRECISION) for v in all_values]
        else:
            all_values = [int(round(v)) for v in all_values]

        # Ensure unique values
        all_values = list(dict.fromkeys(all_values))  # Remove duplicates, preserve order
        
        # Fill if needed (but mark as placeholders for validation to catch)
        while len(all_values) < 4:
            new_val = answer_num + len(all_values) + random.randint(1, 5)
            if new_val not in all_values:
                all_values.append(int(new_val) if isinstance(answer_num, int) else round(new_val, ANSWER_PRECISION))

        # Format with unit
        options = [f"{v} {unit}".strip() for v in all_values[:4]]
        
        # Shuffle
        correct_value = f"{all_values[0]} {unit}".strip()
        random.shuffle(options)
        correct_idx = options.index(correct_value)

        return options, correct_idx

    def _generate_coordinate_options(
        self,
        blueprint: Blueprint,
        answer: Any,
        answer_display: str,
        variables: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        """
        Generate options for coordinate-type questions.
        Answer should be formatted as (x, y) tuple.
        """
        # If answer_options are predefined, use them
        if blueprint.answer_options and len(blueprint.answer_options) >= 4:
            options = list(blueprint.answer_options[:4])
            random.shuffle(options)
            correct_idx = self._find_correct_index(options, answer_display, answer)
            return options, correct_idx
        
        # Try to parse answer as coordinate
        if isinstance(answer, (tuple, list)) and len(answer) == 2:
            x, y = answer
            correct = f"({x}, {y})"
            
            # Generate coordinate distractors (common errors)
            distractors = [
                f"({y}, {x})",           # Swapped coordinates
                f"({-x}, {y})",          # Sign error on x
                f"({x}, {-y})",          # Sign error on y
                f"({x + 1}, {y})",       # Off by one
                f"({x}, {y + 1})",       # Off by one
            ]
            
            # Take unique distractors
            options = [correct]
            for d in distractors:
                if d not in options and len(options) < 4:
                    options.append(d)
            
            random.shuffle(options)
            correct_idx = options.index(correct)
            return options, correct_idx
        
        # Fallback: treat as categorical
        return self._generate_categorical_options(blueprint, answer_display, variables)

    def _generate_expression_options(
        self,
        blueprint: Blueprint,
        answer_display: str,
        variables: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        """
        Generate options for expression-type questions.
        Must have predefined answer_options (expressions can't be auto-generated).
        """
        # Expression questions MUST have answer_options
        if blueprint.answer_options and len(blueprint.answer_options) >= 4:
            options = list(blueprint.answer_options[:4])
            random.shuffle(options)
            correct_idx = self._find_correct_index(options, answer_display, None)
            return options, correct_idx
        
        # No answer_options = broken blueprint
        print(f"ERROR: Expression question {blueprint.id} has no answer_options")
        return [answer_display, "__PLACEHOLDER_1__", "__PLACEHOLDER_2__", "__PLACEHOLDER_3__"], 0

    def _generate_distractors(
        self,
        blueprint: Blueprint,
        correct_answer: float,
        variables: Dict[str, Any]
    ) -> List[float]:
        """
        Generate distractor values using blueprint-defined strategies.
        
        ONLY from blueprint's distractor_strategy formulas.
        These formulas mimic real student mistakes.
        """
        distractors = []
        
        # Check if blueprint has distractor strategies
        if blueprint.options and hasattr(blueprint.options, 'distractor_strategy'):
            strategies = blueprint.options.distractor_strategy
            
            if strategies:
                eval_context = {
                    'math': math,
                    'sqrt': math.sqrt,
                    'correct': correct_answer,
                    'ans': correct_answer,
                    **variables
                }
                
                for strategy in strategies[:3]:  # Use up to 3 distractors
                    try:
                        if hasattr(strategy, 'formula') and strategy.formula:
                            formula = strategy.formula
                            distractor = eval(formula, {"__builtins__": {}}, eval_context)
                            
                            # Validate distractor
                            if self._is_valid_distractor(distractor, correct_answer, distractors):
                                distractors.append(distractor)
                    except Exception as e:
                        print(f"Distractor formula failed: {e}")
                        continue

        # If not enough distractors, use common error patterns
        if len(distractors) < 3:
            fallback = self._generate_common_error_distractors(correct_answer, variables)
            for d in fallback:
                if len(distractors) >= 3:
                    break
                if self._is_valid_distractor(d, correct_answer, distractors):
                    distractors.append(d)

        return distractors[:3]

    def _generate_common_error_distractors(
        self,
        correct_answer: float,
        variables: Dict[str, Any]
    ) -> List[float]:
        """
        Generate distractors based on common student mistakes.
        
        These are formula-driven, not random:
        - Sign errors
        - Factor of 2 errors
        - Off-by-one errors
        - Missing/extra pi or sqrt
        """
        distractors = []
        
        # Common error patterns
        patterns = [
            correct_answer * 2,        # Forgot to divide by 2
            correct_answer / 2,        # Divided extra time
            correct_answer + 1,        # Off by one
            correct_answer - 1,        # Off by one
            -correct_answer,           # Sign error
            correct_answer * math.pi,  # Applied pi incorrectly
            correct_answer / math.pi,  # Forgot pi
            math.sqrt(abs(correct_answer)) if correct_answer >= 0 else correct_answer,  # Sqrt confusion
            correct_answer ** 2,       # Squared instead of sqrt
        ]
        
        # Filter valid ones
        for p in patterns:
            if self._is_valid_distractor(p, correct_answer, distractors):
                distractors.append(p)

        return distractors

    def _is_valid_distractor(
        self,
        distractor: float,
        correct_answer: float,
        existing: List[float]
    ) -> bool:
        """Check if distractor is valid (not duplicate, not absurd)."""
        if distractor is None:
            return False
            
        # Not too close to correct answer
        if abs(distractor - correct_answer) < 0.01:
            return False
        
        # Not duplicate of existing
        for e in existing:
            if abs(distractor - e) < 0.01:
                return False
        
        # Not absurdly large or small relative to answer
        if correct_answer != 0:
            ratio = abs(distractor / correct_answer)
            if ratio > 100 or ratio < 0.01:
                return False
        
        return True

    def _generate_categorical_options(
        self,
        blueprint: Blueprint,
        correct_answer: str,
        variables: Dict[str, Any]
    ) -> Tuple[List[str], int]:
        """
        Generate options for categorical/text answers.
        
        STRICT POLICY: Never use placeholder text like "Option A".
        If we can't generate 4 real options, return failure markers.
        """
        options = []
        
        # Try to get from options config
        if blueprint.options and hasattr(blueprint.options, 'values'):
            options = list(getattr(blueprint.options, 'values', []))
        
        # Try answer_options from blueprint
        if not options and blueprint.answer_options:
            options = list(blueprint.answer_options)
        
        # Ensure correct answer is included
        if correct_answer and correct_answer not in options and correct_answer != "N/A":
            options.append(correct_answer)
        
        # If we don't have at least 4 real options, mark as incomplete
        # This will be caught by validation and cause retry
        if len(options) < 4:
            print(f"WARNING: Blueprint {blueprint.id} has insufficient options ({len(options)}/4)")
            # Mark these as PLACEHOLDER so validation can catch them
            while len(options) < 4:
                options.append(f"__PLACEHOLDER_{len(options)}__")
        
        options = options[:4]
        random.shuffle(options)
        
        correct_idx = 0
        for i, opt in enumerate(options):
            if opt == correct_answer:
                correct_idx = i
                break

        return options, correct_idx

    def _find_correct_index(
        self,
        options: List[str],
        answer_display: str,
        answer: Any
    ) -> int:
        """Find index of correct answer in options list."""
        # Exact match
        for i, opt in enumerate(options):
            if opt.strip() == answer_display.strip():
                return i

        # Numeric comparison
        try:
            correct_num = float(str(answer).split()[0])
            for i, opt in enumerate(options):
                opt_num = float(opt.split()[0])
                if abs(correct_num - opt_num) < 0.01:
                    return i
        except (ValueError, IndexError):
            pass

        return 0

    def _is_numeric(self, value: str) -> bool:
        """Check if string represents a number."""
        try:
            float(value.split()[0])
            return True
        except (ValueError, IndexError):
            return False

    # =========================================================================
    # PHASE 4: VALIDATION & QUALITY GATE
    # =========================================================================

    def _validate_question(
        self,
        question: GeneratedQuestion,
        blueprint: Blueprint,
        variables: Dict[str, Any],
        computed_answer: Any
    ) -> ValidationResult:
        """
        Validation gate - no question enters without passing all checks.
        
        Hard Validation (Code):
        1. Formula re-evaluation
        2. Constraint checks
        3. Option uniqueness
        4. Time feasibility check
        """
        errors = []
        warnings = []

        # 1. RE-EVALUATE FORMULA (verify answer is still correct)
        if blueprint.formula and computed_answer is not None:
            re_answer, _ = self._compute_answer(blueprint, variables)
            if re_answer is not None:
                try:
                    if abs(float(re_answer) - float(computed_answer)) > 0.01:
                        errors.append("Answer re-verification failed")
                except (ValueError, TypeError):
                    if str(re_answer) != str(computed_answer):
                        errors.append("Answer re-verification failed (non-numeric)")

        # 2. CHECK ALL OPTIONS ARE UNIQUE
        if len(question.options) != len(set(question.options)):
            errors.append("Duplicate options detected")

        # 3. VERIFY CORRECT OPTION INDEX IS VALID
        if question.correct_option_index >= len(question.options):
            errors.append("Invalid correct option index")

        # 4. CHECK CORRECT ANSWER IS IN OPTIONS
        correct_opt = question.options[question.correct_option_index] if question.options else ""
        if question.correct_answer not in correct_opt and not self._answers_match(
            question.correct_answer, correct_opt
        ):
            warnings.append("Correct answer may not match selected option")

        # 5. QUESTION TEXT NOT EMPTY
        if not question.question_text or len(question.question_text.strip()) < 10:
            errors.append("Question text too short or empty")

        # 6. TIME FEASIBILITY (warning only)
        if blueprint.constraints.expected_time_sec < 20:
            warnings.append("Expected time seems too short")

        # 7. CHECK FOR PLACEHOLDER OPTIONS
        placeholder_patterns = ["__PLACEHOLDER_", "Option A", "Option B", "Option C", "Option D", "N/A"]
        for opt in question.options:
            for pattern in placeholder_patterns:
                if pattern in str(opt):
                    errors.append(f"Placeholder option detected: {opt}")
                    break

        # 8. CHECK ANSWER IS NOT N/A OR ERROR
        if question.correct_answer in ["N/A", "Error", None, ""]:
            errors.append("Invalid correct answer")

        # 9. CHECK FOR MAGNITUDE SANITY (prevent 100x errors)
        if computed_answer is not None and isinstance(computed_answer, (int, float)):
            # Check if any option values are wildly different from answer
            try:
                answer_magnitude = abs(computed_answer) if computed_answer != 0 else 1
                for opt in question.options:
                    opt_val = float(str(opt).split()[0])
                    if answer_magnitude > 0:
                        ratio = abs(opt_val) / answer_magnitude if opt_val != 0 else 0
                        if ratio > 1000 or (ratio < 0.001 and ratio > 0):
                            warnings.append(f"Magnitude mismatch: answer={computed_answer}, option={opt_val}")
            except (ValueError, TypeError, ZeroDivisionError):
                pass  # Non-numeric options, skip this check

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _answers_match(self, answer1: str, answer2: str) -> bool:
        """Check if two answers match (handles numeric comparison)."""
        try:
            num1 = float(answer1.split()[0])
            num2 = float(answer2.split()[0])
            return abs(num1 - num2) < 0.01
        except (ValueError, IndexError):
            return answer1.strip() == answer2.strip()

    def validate_with_ai(
        self,
        question: GeneratedQuestion,
        blueprint: Blueprint
    ) -> Tuple[bool, str]:
        """
        Optional soft validation using AI as reviewer.
        
        Prompt: "Is this question solvable within X seconds? Is wording clear?"
        Returns: (OK/Not OK, Reason)
        """
        if not self.llm_client:
            return True, "AI validation not available"

        try:
            time_limit = blueprint.constraints.expected_time_sec if blueprint.constraints else 60
            
            prompt = f"""Review this TS EAMCET exam question:

Question: {question.question_text}
Options: {', '.join(question.options)}
Expected solve time: {time_limit} seconds

Is this question:
1. Solvable within {time_limit} seconds by a TS EAMCET student?
2. Worded clearly and unambiguously?
3. Mathematically/scientifically correct?

Reply ONLY with:
OK - if all criteria are met
NOT OK: [brief reason] - if any issue

Your response:"""

            completion = self.llm_client.chat.completions.create(
                model=self.llm_model,
                temperature=0.0,
                max_tokens=100,
                messages=[
                    {"role": "system", "content": "You are a strict TS EAMCET exam reviewer."},
                    {"role": "user", "content": prompt},
                ],
            )

            response = completion.choices[0].message.content.strip()
            is_ok = response.upper().startswith("OK")
            
            return is_ok, response

        except Exception as e:
            return True, f"AI validation failed: {e}"

    # =========================================================================
    # SOLUTION GENERATION
    # =========================================================================

    def _generate_solution(
        self,
        blueprint: Blueprint,
        variables: Dict[str, Any],
        answer: Any
    ) -> str:
        """Generate step-by-step solution."""
        if blueprint.solution_template:
            solution_vars = {**variables, 'answer': answer}
            return self._fill_template(blueprint.solution_template, solution_vars)

        # Build basic solution
        parts = []

        if blueprint.formula:
            parts.append(f"Using: {blueprint.formula}")

        # Variable values
        var_strs = [f"{k}={v}" for k, v in variables.items() if not isinstance(v, dict)]
        if var_strs:
            parts.append(f"Given: {', '.join(var_strs)}")

        parts.append(f"Answer: {answer}")

        return "\n".join(parts)

    # =========================================================================
    # SINGLE QUESTION BY ID
    # =========================================================================

    def generate_by_id(
        self,
        blueprint_id: str,
        seed: Optional[int] = None,
        use_ai_phrasing: bool = False,
    ) -> Optional[GeneratedQuestion]:
        """
        Generate a question from a blueprint ID.
        
        Args:
            blueprint_id: The blueprint ID
            seed: Random seed for reproducibility
            use_ai_phrasing: If True, use AI to improve question text phrasing
            
        Returns:
            Generated question or None if blueprint not found
        """
        blueprint = self.loader.get_blueprint(blueprint_id)
        if blueprint is None:
            return None
        return self.generate_from_blueprint(blueprint, seed=seed, use_ai_phrasing=use_ai_phrasing)

    # =========================================================================
    # BATCH GENERATION
    # =========================================================================

    def generate_batch(
        self,
        count: int,
        subject: Optional[str] = None,
        section: Optional[str] = None,
        topic: Optional[str] = None,
        chapter: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        tags: Optional[List[str]] = None,
        unique_blueprints: bool = True,
        use_ai_phrasing: bool = False,
    ) -> List[GeneratedQuestion]:
        """Generate multiple questions."""
        blueprints = self.loader.query_blueprints(
            subject=subject,
            section=section,
            topic=topic,
            chapter=chapter,
            difficulty=difficulty,
            tags=tags,
        )

        if not blueprints:
            return []

        questions = []
        used_blueprints = set()

        for _ in range(count):
            available = [
                bp for bp in blueprints
                if not unique_blueprints or bp.id not in used_blueprints
            ]

            if not available:
                available = blueprints
                used_blueprints.clear()

            blueprint = random.choice(available)
            used_blueprints.add(blueprint.id)

            question = self.generate_from_blueprint(
                blueprint,
                use_ai_phrasing=use_ai_phrasing
            )
            
            if question:
                questions.append(question)

        return questions

    def generate_test(
        self,
        distribution: Dict[str, int],
        difficulty_mix: Optional[Dict[str, float]] = None
    ) -> List[GeneratedQuestion]:
        """Generate a complete test with subject distribution."""
        if difficulty_mix is None:
            difficulty_mix = {"easy": 0.3, "moderate": 0.5, "hard": 0.2}

        all_questions = []

        for subject, count in distribution.items():
            easy_count = int(count * difficulty_mix.get("easy", 0.33))
            hard_count = int(count * difficulty_mix.get("hard", 0.33))
            moderate_count = count - easy_count - hard_count

            for diff, diff_count in [
                (DifficultyLevel.EASY, easy_count),
                (DifficultyLevel.MODERATE, moderate_count),
                (DifficultyLevel.HARD, hard_count),
            ]:
                if diff_count > 0:
                    questions = self.generate_batch(
                        count=diff_count,
                        subject=subject,
                        difficulty=diff,
                    )
                    all_questions.extend(questions)

        random.shuffle(all_questions)
        return all_questions


# =============================================================================
# SINGLETON
# =============================================================================

_generator_v2_instance: Optional[QuestionGeneratorV2] = None


def get_question_generator_v2() -> QuestionGeneratorV2:
    """Get singleton instance of QuestionGeneratorV2."""
    global _generator_v2_instance
    if _generator_v2_instance is None:
        _generator_v2_instance = QuestionGeneratorV2()
    return _generator_v2_instance
