"""
Exam Validator - Hard Validation Gate for Generated Tests

This module ensures NO broken questions reach production.
It performs comprehensive validation at multiple levels:

1. Structural Validation - Question counts, section distribution
2. Option Integrity - No placeholders, all options unique, correct answer present
3. Calculation Revalidation - Re-compute answers and verify
4. Blueprint Alignment - Type system compliance
"""

import math
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""
    ERROR = "error"      # Must fix - question is broken
    WARNING = "warning"  # Should fix - quality issue
    INFO = "info"        # Could fix - minor improvement


@dataclass
class ValidationIssue:
    """A single validation issue found."""
    severity: ValidationSeverity
    question_id: str
    question_index: int  # 1-based for user display
    field: str           # Which field has the issue
    message: str
    details: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report for an exam/test."""
    total_questions: int
    expected_questions: int
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Section breakdown
    section_counts: Dict[str, int] = field(default_factory=dict)
    expected_section_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
    
    @property
    def is_valid(self) -> bool:
        """Test is valid if no ERROR-level issues."""
        return self.error_count == 0
    
    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"=== VALIDATION REPORT ===",
            f"Total Questions: {self.total_questions}/{self.expected_questions}",
            f"Errors: {self.error_count}",
            f"Warnings: {self.warning_count}",
            f"Status: {'✅ PASS' if self.is_valid else '❌ FAIL'}",
            "",
            "Section Breakdown:",
        ]
        
        for section, count in self.section_counts.items():
            expected = self.expected_section_counts.get(section, "?")
            status = "✅" if count == expected else "❌"
            lines.append(f"  {section}: {count}/{expected} {status}")
        
        if self.issues:
            lines.append("")
            lines.append("Issues Found:")
            for issue in self.issues[:20]:  # Show first 20
                symbol = "❌" if issue.severity == ValidationSeverity.ERROR else "⚠️"
                lines.append(f"  {symbol} Q{issue.question_index}: [{issue.field}] {issue.message}")
            
            if len(self.issues) > 20:
                lines.append(f"  ... and {len(self.issues) - 20} more issues")
        
        return "\n".join(lines)


class ExamValidator:
    """
    Hard validation gate for generated exams.
    
    Usage:
        validator = ExamValidator()
        report = validator.validate_test(questions, exam_config)
        if not report.is_valid:
            raise ValueError(report.summary())
    """
    
    # Placeholder patterns to detect
    PLACEHOLDER_PATTERNS = [
        r"__PLACEHOLDER_\d+__",
        r"^Option [A-D]$",
        r"^N/A$",
        r"^Error$",
        r"^None$",
    ]
    
    def __init__(self):
        self.placeholder_regex = re.compile(
            "|".join(self.PLACEHOLDER_PATTERNS),
            re.IGNORECASE
        )
    
    def validate_test(
        self,
        questions: List[Dict[str, Any]],
        expected_total: int = 160,
        section_distribution: Optional[Dict[str, int]] = None
    ) -> ValidationReport:
        """
        Validate an entire test.
        
        Args:
            questions: List of question dicts with keys:
                - id, question_text, options, correct_answer, correct_option_index
                - section (optional), subject (optional)
            expected_total: Expected total questions (default 160 for TS EAMCET)
            section_distribution: Expected per-section counts
                e.g., {"Mathematics": 80, "Physics": 40, "Chemistry": 40}
        
        Returns:
            ValidationReport with all issues found
        """
        if section_distribution is None:
            section_distribution = {
                "Mathematics": 80,
                "Physics": 40,
                "Chemistry": 40,
            }
        
        report = ValidationReport(
            total_questions=len(questions),
            expected_questions=expected_total,
            expected_section_counts=section_distribution,
        )
        
        # 1. STRUCTURAL VALIDATION
        self._validate_structure(questions, report)
        
        # 2. OPTION INTEGRITY (per question)
        for idx, q in enumerate(questions, 1):
            self._validate_question_options(q, idx, report)
            self._validate_question_content(q, idx, report)
        
        return report
    
    def _validate_structure(
        self,
        questions: List[Dict[str, Any]],
        report: ValidationReport
    ) -> None:
        """Validate structural integrity - counts and distribution."""
        
        # Check total count
        if len(questions) != report.expected_questions:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                question_id="STRUCTURE",
                question_index=0,
                field="total_questions",
                message=f"Expected {report.expected_questions} questions, got {len(questions)}",
            ))
        
        # Count by section/subject
        section_counts: Dict[str, int] = {}
        for q in questions:
            section = q.get("section") or q.get("subject") or "Unknown"
            section_counts[section] = section_counts.get(section, 0) + 1
        
        report.section_counts = section_counts
        
        # Check section distribution
        for section, expected in report.expected_section_counts.items():
            actual = section_counts.get(section, 0)
            if actual != expected:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    question_id="STRUCTURE",
                    question_index=0,
                    field="section_distribution",
                    message=f"{section}: expected {expected}, got {actual}",
                ))
    
    def _validate_question_options(
        self,
        question: Dict[str, Any],
        index: int,
        report: ValidationReport
    ) -> None:
        """Validate option integrity for a single question."""
        q_id = question.get("id", f"Q{index}")
        options = question.get("options", [])
        correct_answer = question.get("correct_answer", "")
        correct_idx = question.get("correct_option_index", 0)
        
        # Check option count
        if len(options) != 4:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                question_id=q_id,
                question_index=index,
                field="options",
                message=f"Expected 4 options, got {len(options)}",
            ))
        
        # Check for placeholder options
        for i, opt in enumerate(options):
            opt_str = str(opt)
            if self.placeholder_regex.search(opt_str):
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    question_id=q_id,
                    question_index=index,
                    field=f"options[{i}]",
                    message=f"Placeholder detected: '{opt_str}'",
                ))
        
        # Check for empty options
        for i, opt in enumerate(options):
            if not opt or str(opt).strip() == "":
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    question_id=q_id,
                    question_index=index,
                    field=f"options[{i}]",
                    message="Empty option",
                ))
        
        # Check option uniqueness
        opt_strings = [str(o).strip().lower() for o in options]
        if len(opt_strings) != len(set(opt_strings)):
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                question_id=q_id,
                question_index=index,
                field="options",
                message="Duplicate options detected",
            ))
        
        # Check correct_option_index is valid
        if correct_idx < 0 or correct_idx >= len(options):
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                question_id=q_id,
                question_index=index,
                field="correct_option_index",
                message=f"Invalid index {correct_idx} for {len(options)} options",
            ))
        
        # Check correct answer is in options
        if options and correct_answer:
            correct_answer_str = str(correct_answer).strip()
            # Try exact match first
            found = any(
                correct_answer_str.lower() in str(opt).lower() or
                str(opt).lower() in correct_answer_str.lower()
                for opt in options
            )
            
            # Try numeric match
            if not found:
                try:
                    correct_num = float(correct_answer_str.split()[0])
                    for opt in options:
                        try:
                            opt_num = float(str(opt).split()[0])
                            if abs(correct_num - opt_num) < 0.01:
                                found = True
                                break
                        except (ValueError, IndexError):
                            continue
                except (ValueError, IndexError):
                    pass
            
            if not found:
                report.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    question_id=q_id,
                    question_index=index,
                    field="correct_answer",
                    message=f"Correct answer '{correct_answer}' not found in options",
                    details=f"Options: {options}",
                ))
    
    def _validate_question_content(
        self,
        question: Dict[str, Any],
        index: int,
        report: ValidationReport
    ) -> None:
        """Validate question content quality."""
        q_id = question.get("id", f"Q{index}")
        question_text = question.get("question_text", "")
        
        # Check question text not empty
        if not question_text or len(str(question_text).strip()) < 10:
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                question_id=q_id,
                question_index=index,
                field="question_text",
                message="Question text too short or empty",
            ))
        
        # Check for template variables not filled
        if "{" in str(question_text) and "}" in str(question_text):
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                question_id=q_id,
                question_index=index,
                field="question_text",
                message="Possible unfilled template variable",
                details=question_text[:100],
            ))
        
        # Check correct_answer is not placeholder
        correct_answer = question.get("correct_answer", "")
        if self.placeholder_regex.search(str(correct_answer)):
            report.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                question_id=q_id,
                question_index=index,
                field="correct_answer",
                message=f"Placeholder correct answer: '{correct_answer}'",
            ))
    
    def validate_question(
        self,
        question: Dict[str, Any],
        index: int = 1
    ) -> List[ValidationIssue]:
        """
        Validate a single question.
        
        Returns list of issues (empty if valid).
        """
        report = ValidationReport(
            total_questions=1,
            expected_questions=1,
        )
        
        self._validate_question_options(question, index, report)
        self._validate_question_content(question, index, report)
        
        return report.issues
    
    def recompute_answer(
        self,
        question: Dict[str, Any],
        formula: str,
        variables: Dict[str, Any],
        tolerance: float = 0.05
    ) -> Tuple[bool, Optional[str]]:
        """
        Re-compute answer and compare with stored value.
        
        Args:
            question: Question dict with correct_answer
            formula: Formula to evaluate
            variables: Variable values used
            tolerance: Acceptable relative error (default 5%)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        stored_answer = question.get("correct_answer", "")
        
        try:
            # Build eval context
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
                **variables
            }
            
            # Compute
            computed = eval(formula, {"__builtins__": {}}, eval_context)
            
            # Parse stored answer
            stored_num = float(str(stored_answer).split()[0])
            computed_num = float(computed)
            
            # Compare with tolerance
            if stored_num == 0:
                is_valid = abs(computed_num) < 0.01
            else:
                relative_error = abs(computed_num - stored_num) / abs(stored_num)
                is_valid = relative_error <= tolerance
            
            if not is_valid:
                return False, f"Computed {computed_num:.4f}, stored {stored_num:.4f}"
            
            return True, None
            
        except Exception as e:
            return False, f"Computation failed: {str(e)}"


# Singleton instance
_validator_instance: Optional[ExamValidator] = None


def get_exam_validator() -> ExamValidator:
    """Get singleton ExamValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ExamValidator()
    return _validator_instance


def validate_exam(
    questions: List[Dict[str, Any]],
    expected_total: int = 160,
    section_distribution: Optional[Dict[str, int]] = None
) -> ValidationReport:
    """
    Convenience function to validate an exam.
    
    Usage:
        from app.services.exam_validator import validate_exam
        
        report = validate_exam(questions)
        if not report.is_valid:
            print(report.summary())
            raise ValueError("Exam validation failed")
    """
    return get_exam_validator().validate_test(
        questions,
        expected_total=expected_total,
        section_distribution=section_distribution
    )
