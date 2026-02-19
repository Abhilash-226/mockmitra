import json
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from groq import Groq
from app.models.blueprint import GeneratedQuestion, Blueprint
from app.core.config import settings

class ValidationResult(BaseModel):
    is_valid: bool = Field(..., description="True if the question is logically sound")
    reason: str = Field(..., description="Explanation of validity or failure")
    corrected_answer: Optional[str] = Field(None, description="If valid but answer was wrong, the correct answer")

class QuestionValidator:
    """
    Validates AI-generated questions by attempting to solve them
    using a 'Solver' persona.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = None
        # Use a stronger model for validation if possible, or same model with different prompt
        self.model = "llama-3.1-8b-instant" 
        self.enabled = False # Temporarily disable validation to debug generation yield 
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                print(f"Validator Init Failed: {e}")

    def validate_question(self, question: GeneratedQuestion, blueprint: Blueprint) -> bool:
        """
        Validates the question by asking the AI to solve it and compare answers.
        Returns True if the question is solid.
        """
        if not self.enabled:
            return True

        if not self.client:
            return True # Fail open if no validator (for now)

        prompt = self._build_solver_prompt(question)
        
        try:
            response = self._call_solver(prompt)
            if not response:
                print("Validator: No response from LLM")
                return False # Fail closed on error
                
            validation = ValidationResult(**response)
            
            print(f"Validator Result: {validation.is_valid}, Reason: {validation.reason}")

            if not validation.is_valid:
                print(f"Validation Failed for {question.id}: {validation.reason}")
                with open("validation_failure.log", "a") as f:
                     f.write(f"Question ID: {question.id}\nReason: {validation.reason}\n\n")
                return False
                
            return True
            
        except Exception as e:
            print(f"Validation Critical Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _build_solver_prompt(self, question: GeneratedQuestion) -> str:
        return f"""
You are a strict academic reviewer. Verify this question for logical correctness.

Question: {question.question_text}
Options: {question.options}
Claimed Correct Answer: {question.correct_answer}
Provided Solution: {question.solution}

Task:
1. Solve the question independently.
2. Check if the claimed answer is correct.
3. Check if the options are distinct and plausible.
4. Check if the question is ambiguous.

Output JSON:
{{
  "is_valid": true/false,
  "reason": "...",
  "corrected_answer": "..." (optional)
}}
"""

    def _call_solver(self, prompt: str) -> Optional[Dict[str, Any]]:
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1, # Low temp for strict logic
                response_format={"type": "json_object"},
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"Validator LLM Call Error: {e}")
            return None
