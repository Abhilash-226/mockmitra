"""
Utility functions for PYQ extraction.
"""
import re
from pathlib import Path
from typing import Tuple, Optional


def parse_pdf_filename(filename: str) -> Tuple[int, int]:
    """
    Parse PDF filename to extract year and shift.
    
    Examples:
        2024.pdf -> (2024, 1)
        2024-1.pdf -> (2024, 1)
        2024-2.pdf -> (2024, 2)
    
    Returns:
        Tuple of (year, shift)
    """
    name = Path(filename).stem  # Remove .pdf extension
    
    if '-' in name:
        parts = name.split('-')
        year = int(parts[0])
        shift = int(parts[1])
    else:
        year = int(name)
        shift = 1
    
    return year, shift


def generate_paper_id(exam_code: str, year: int, shift: int) -> str:
    """Generate a standardized paper ID."""
    return f"{exam_code}_{year}_{shift}"


def sanitize_text(text: str) -> str:
    """
    Clean up extracted text.
    - Remove excessive whitespace
    - Fix common OCR issues
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Fix common issues
    text = text.replace('\\n', '\n')
    
    return text


def validate_question(question: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a question structure.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ['text', 'options', 'correct']
    
    for field in required_fields:
        if field not in question:
            return False, f"Missing required field: {field}"
    
    # Check options
    options = question.get('options', {})
    if not isinstance(options, dict):
        return False, "Options must be a dictionary"
    
    if len(options) < 2:
        return False, "Question must have at least 2 options"
    
    # Check correct answer
    correct = question.get('correct', '')
    if correct not in options:
        return False, f"Correct answer '{correct}' not in options"
    
    return True, None


def estimate_section(question_number: int, distribution: dict) -> str:
    """
    Estimate section based on question number and expected distribution.
    
    Args:
        question_number: 1-indexed question number
        distribution: Dict mapping section code to question count
                     e.g., {"MAT": 80, "PHY": 40, "CHE": 40}
    
    Returns:
        Section code
    """
    cumulative = 0
    for section_code, count in distribution.items():
        cumulative += count
        if question_number <= cumulative:
            return section_code
    
    # Default to last section if number exceeds total
    return list(distribution.keys())[-1]
