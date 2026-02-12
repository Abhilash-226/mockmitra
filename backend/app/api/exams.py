from fastapi import APIRouter, HTTPException
from typing import List
import yaml
from pathlib import Path

from app.schemas.exam import ExamConfig, ExamListResponse
from app.core.config import settings

router = APIRouter()


def load_exam_config(exam_code: str) -> ExamConfig:
    """Load exam configuration from YAML file"""
    config_path = Path(settings.EXAM_CONFIGS_PATH) / f"{exam_code}.yaml"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Exam config not found: {exam_code}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return ExamConfig(**data)


def get_all_exam_configs() -> List[ExamConfig]:
    """Load all exam configurations"""
    print("DEBUG: Entered get_all_exam_configs")
    configs_dir = Path(settings.EXAM_CONFIGS_PATH)
    print(f"DEBUG: configs_dir={configs_dir}")
    configs = []
    if configs_dir.exists():
        print("DEBUG: configs_dir exists")
        for config_file in configs_dir.glob("*.yaml"):
            print(f"DEBUG: Loading {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                print(f"DEBUG: YAML loaded for {config_file}")
                configs.append(ExamConfig(**data))
                print(f"DEBUG: ExamConfig created for {config_file}")
    else:
        print("DEBUG: configs_dir does NOT exist")
    print(f"DEBUG: Returning {len(configs)} configs")
    return configs


@router.get("/", response_model=List[ExamListResponse])
@router.get("", response_model=List[ExamListResponse])
async def list_exams():
    print("DEBUG: Entered list_exams endpoint")
    configs = get_all_exam_configs()
    print(f"DEBUG: configs loaded, count={len(configs)}")
    # Only include exams for which blueprints exist
    blueprint_exam_codes = {"ts_eamcet"}
    filtered_configs = [config for config in configs if config.exam_code in blueprint_exam_codes]
    result = [
        ExamListResponse(
            exam_code=config.exam_code,
            exam_name=config.exam_name,
            description=config.description,
            total_questions=config.total_questions,
            duration_minutes=config.total_duration_minutes,
            sections=[s.name for s in config.sections]
        )
        for config in filtered_configs
    ]
    print(f"DEBUG: Returning {len(result)} ExamListResponse objects (filtered)")
    return result


@router.get("/{exam_code}", response_model=ExamConfig)
async def get_exam(exam_code: str):
    """Get detailed exam configuration"""
    return load_exam_config(exam_code)


@router.get("/{exam_code}/sections")
async def get_exam_sections(exam_code: str):
    """Get sections for an exam"""
    config = load_exam_config(exam_code)
    return config.sections


@router.get("/{exam_code}/instructions")
async def get_exam_instructions(exam_code: str):
    """Get instructions for an exam"""
    config = load_exam_config(exam_code)
    return {
        "exam_name": config.exam_name,
        "instructions": config.instructions,
        "duration_minutes": config.total_duration_minutes,
        "total_questions": config.total_questions,
        "total_marks": config.total_marks
    }
