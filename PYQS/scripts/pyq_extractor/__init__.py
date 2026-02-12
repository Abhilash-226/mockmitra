"""
PYQ Extractor Module
Uses AI (Gemini Vision) to extract questions from PDF papers.
"""

from .gemini_extractor import GeminiExtractor
from .config import ExamConfig, get_exam_config

__all__ = ['GeminiExtractor', 'ExamConfig', 'get_exam_config']
