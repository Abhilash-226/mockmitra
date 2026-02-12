"""
Blueprint Loader Service
Loads and manages question blueprints from YAML files.
"""

import os
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

from app.models.blueprint import Blueprint, DifficultyLevel


class BlueprintLoader:
    """
    Service to load, validate, and query question blueprints.
    """
    
    def __init__(self, blueprints_dir: Optional[str] = None):
        """
        Initialize the blueprint loader.
        
        Args:
            blueprints_dir: Path to blueprints directory. 
                           Defaults to backend/blueprints/
        """
        if blueprints_dir is None:
            # Default to backend/blueprints relative to this file
            base_dir = Path(__file__).parent.parent.parent
            blueprints_dir = base_dir / "blueprints"
        
        self.blueprints_dir = Path(blueprints_dir)
        self._blueprints: Dict[str, Blueprint] = {}
        self._loaded = False
    
    def load_all(self, force_reload: bool = False) -> int:
        """
        Load all blueprint YAML files from the blueprints directory.
        
        Args:
            force_reload: If True, reload even if already loaded
            
        Returns:
            Number of blueprints loaded
        """
        if self._loaded and not force_reload:
            return len(self._blueprints)
        
        self._blueprints.clear()
        
        if not self.blueprints_dir.exists():
            raise FileNotFoundError(f"Blueprints directory not found: {self.blueprints_dir}")
        
        # Load all YAML files recursively from exam subfolders
        for yaml_file in self.blueprints_dir.glob("**/*.yaml"):
            self._load_file(yaml_file)
        
        for yml_file in self.blueprints_dir.glob("**/*.yml"):
            self._load_file(yml_file)
        
        self._loaded = True
        return len(self._blueprints)
    
    def _load_file(self, file_path: Path) -> None:
        """Load blueprints from a single YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return
            
            # Handle both list format and dict format
            if isinstance(data, list):
                blueprints_data = data
            elif isinstance(data, dict):
                blueprints_data = data.get('blueprints', [data])
            else:
                return
            
            for bp_data in blueprints_data:
                try:
                    blueprint = Blueprint(**bp_data)
                    self._blueprints[blueprint.id] = blueprint
                except Exception as e:
                    print(f"Warning: Failed to load blueprint from {file_path}: {e}")
                    continue
                    
        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse YAML file {file_path}: {e}")
        except Exception as e:
            print(f"Warning: Error loading {file_path}: {e}")
    
    def get_blueprint(self, blueprint_id: str) -> Optional[Blueprint]:
        """
        Get a specific blueprint by ID.
        
        Args:
            blueprint_id: The unique blueprint ID
            
        Returns:
            Blueprint if found, None otherwise
        """
        self._ensure_loaded()
        return self._blueprints.get(blueprint_id)
    
    def get_all_blueprints(self) -> List[Blueprint]:
        """Get all loaded blueprints."""
        self._ensure_loaded()
        return list(self._blueprints.values())
    
    def get_blueprints_by_subject(self, subject: str) -> List[Blueprint]:
        """
        Get all blueprints for a specific subject.
        
        Args:
            subject: Subject name (e.g., "Mathematics", "Physics", "Chemistry")
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        return [
            bp for bp in self._blueprints.values()
            if bp.subject.lower() == subject.lower()
        ]
    
    def get_blueprints_by_chapter(self, chapter: str) -> List[Blueprint]:
        """
        Get all blueprints for a specific chapter.
        
        Args:
            chapter: Chapter name
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        return [
            bp for bp in self._blueprints.values()
            if bp.chapter.lower() == chapter.lower()
        ]
    
    def get_blueprints_by_unit(self, unit: str) -> List[Blueprint]:
        """
        Get all blueprints for a specific unit.
        
        Args:
            unit: Unit name
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        return [
            bp for bp in self._blueprints.values()
            if bp.unit and bp.unit.lower() == unit.lower()
        ]
    
    def get_blueprints_by_difficulty(self, difficulty: DifficultyLevel) -> List[Blueprint]:
        """
        Get all blueprints with a specific difficulty level.
        
        Args:
            difficulty: Difficulty level (easy, moderate, hard)
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        difficulty_value = difficulty.value if hasattr(difficulty, 'value') else str(difficulty)
        return [
            bp for bp in self._blueprints.values()
            if self._difficulty_matches(bp.difficulty_level, difficulty_value)
        ]
    
    def _difficulty_matches(self, bp_difficulty, target_difficulty: str) -> bool:
        """Helper to compare difficulty levels."""
        if bp_difficulty is None:
            return False
        if hasattr(bp_difficulty, 'value'):
            return bp_difficulty.value == target_difficulty
        return str(bp_difficulty) == target_difficulty
    
    def get_blueprints_by_tag(self, tag: str) -> List[Blueprint]:
        """
        Get all blueprints containing a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        return [
            bp for bp in self._blueprints.values()
            if bp.tags and tag.lower() in [t.lower() for t in bp.tags]
        ]
    
    def query_blueprints(
        self,
        exam: Optional[str] = None,
        subject: Optional[str] = None,
        unit: Optional[str] = None,
        chapter: Optional[str] = None,
        concept: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Blueprint]:
        """
        Query blueprints with multiple filters.
        
        Args:
            exam: Filter by exam (e.g., "TS_EAMCET", "SSC_CGL")
            subject: Filter by subject
            unit: Filter by unit
            chapter: Filter by chapter
            concept: Filter by concept (partial match)
            difficulty: Filter by difficulty level
            tags: Filter by tags (any match)
            limit: Maximum number of results
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        results = list(self._blueprints.values())
        
        if exam:
            results = [bp for bp in results if bp.exam and bp.exam.lower() == exam.lower()]
        
        if subject:
            results = [bp for bp in results if bp.subject.lower() == subject.lower()]
        
        if unit:
            results = [bp for bp in results if bp.unit and bp.unit.lower() == unit.lower()]
        
        if chapter:
            results = [bp for bp in results if bp.chapter.lower() == chapter.lower()]
        
        if concept:
            results = [
                bp for bp in results 
                if bp.concept and concept.lower() in bp.concept.lower()
            ]
        
        if difficulty:
            difficulty_value = difficulty.value if hasattr(difficulty, 'value') else str(difficulty)
            results = [
                bp for bp in results 
                if self._difficulty_matches(bp.difficulty_level, difficulty_value)
            ]
        
        if tags:
            tag_set = {t.lower() for t in tags}
            results = [
                bp for bp in results 
                if bp.tags and any(t.lower() in tag_set for t in bp.tags)
            ]
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_subjects(self) -> List[str]:
        """Get list of unique subjects."""
        self._ensure_loaded()
        return list(set(bp.subject for bp in self._blueprints.values()))
    
    def get_exams(self) -> List[str]:
        """Get list of unique exams."""
        self._ensure_loaded()
        return list(set(bp.exam for bp in self._blueprints.values() if bp.exam))
    
    def get_blueprints_by_exam(self, exam: str) -> List[Blueprint]:
        """
        Get all blueprints for a specific exam.
        
        Args:
            exam: Exam name (e.g., "TS_EAMCET", "SSC_CGL")
            
        Returns:
            List of matching blueprints
        """
        self._ensure_loaded()
        return [
            bp for bp in self._blueprints.values()
            if bp.exam and bp.exam.lower() == exam.lower()
        ]
    
    def get_chapters_by_subject(self, subject: str) -> List[str]:
        """Get list of chapters for a subject."""
        self._ensure_loaded()
        return list(set(
            bp.chapter for bp in self._blueprints.values()
            if bp.subject.lower() == subject.lower()
        ))
    
    def get_units_by_subject(self, subject: str) -> List[str]:
        """Get list of units for a subject."""
        self._ensure_loaded()
        return list(set(
            bp.unit for bp in self._blueprints.values()
            if bp.subject.lower() == subject.lower() and bp.unit
        ))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded blueprints.
        
        Returns:
            Dictionary with blueprint statistics
        """
        self._ensure_loaded()
        
        by_subject = {}
        by_difficulty = {}
        by_exam = {}
        
        for bp in self._blueprints.values():
            # Count by subject
            by_subject[bp.subject] = by_subject.get(bp.subject, 0) + 1
            
            # Count by exam
            exam_key = bp.exam or "unspecified"
            by_exam[exam_key] = by_exam.get(exam_key, 0) + 1
            
            # Count by difficulty - handle both enum and string
            if bp.difficulty_level:
                if hasattr(bp.difficulty_level, 'value'):
                    diff_key = bp.difficulty_level.value
                else:
                    diff_key = str(bp.difficulty_level)
            else:
                diff_key = "unspecified"
            by_difficulty[diff_key] = by_difficulty.get(diff_key, 0) + 1
        
        return {
            "total_blueprints": len(self._blueprints),
            "by_exam": by_exam,
            "by_subject": by_subject,
            "by_difficulty": by_difficulty,
            "exams": self.get_exams(),
            "subjects": self.get_subjects()
        }
    
    def _ensure_loaded(self) -> None:
        """Ensure blueprints are loaded."""
        if not self._loaded:
            self.load_all()


# Singleton instance
_loader_instance: Optional[BlueprintLoader] = None


def get_blueprint_loader() -> BlueprintLoader:
    """
    Get the singleton BlueprintLoader instance.
    
    Returns:
        BlueprintLoader instance
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = BlueprintLoader()
        _loader_instance.load_all()
    return _loader_instance


def reload_blueprints() -> int:
    """
    Force reload all blueprints.
    
    Returns:
        Number of blueprints loaded
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = BlueprintLoader()
    return _loader_instance.load_all(force_reload=True)
