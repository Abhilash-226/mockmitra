"""
Blueprint Models - Pydantic models for question blueprint validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


class AnswerType(str, Enum):
    """Question answer type - determines how options are generated"""
    NUMERICAL = "numerical"      # Compute answer via formula, generate numeric distractors
    CATEGORICAL = "categorical"  # Choose from predefined answer_options (no computation)
    COORDINATE = "coordinate"    # Answer is a coordinate pair like (x, y)
    EXPRESSION = "expression"    # Answer is a symbolic expression
    BOOLEAN = "boolean"          # True/False type questions


class VariableType(str, Enum):
    INTEGER = "integer"
    FLOAT = "float"
    CHOICE = "choice"
    INTEGER_LIST = "integer_list"


class DistractorStrategy(BaseModel):
    """Distractor option generation strategy"""
    formula: str
    error_type: str


class VariableConfig(BaseModel):
    """Configuration for a single variable"""
    type: Optional[VariableType] = VariableType.INTEGER
    range: Optional[List[int]] = None  # [min, max]
    step: Optional[int] = 1
    values: Optional[List[Any]] = None  # For choice type
    exclude: Optional[List[Any]] = None
    count: Optional[Dict[str, int]] = None  # For lists: {"range": [4, 6]}
    value_range: Optional[List[int]] = None  # For list item values


class Constraints(BaseModel):
    """Question constraints"""
    steps: int = 1
    expected_time_sec: int = 60
    ensure_integer_answer: bool = False
    ensure_perfect_square_sum: bool = False
    ensure_perfect_square_result: bool = False
    answer_range: Optional[List[float]] = None
    r_less_than_n: bool = False  # For permutations


class OptionsConfig(BaseModel):
    """Options/distractors configuration"""
    count: int = 4
    distractor_strategy: List[DistractorStrategy] = []


class SourceReference(BaseModel):
    """Reference to original PYQs"""
    similar_in_years: List[int] = []
    frequency: str = "medium"  # low, medium, high


class Blueprint(BaseModel):
    """Complete question blueprint schema"""
    id: str = Field(..., description="Unique blueprint ID like PHY_CE_01")
    exam: str = Field(default="TS_EAMCET")
    subject: str = Field(..., description="Physics/Chemistry/Mathematics")
    section: Optional[str] = None  # Algebra, Calculus, etc.
    topic: Optional[str] = None    # Functions, Matrices, etc.
    unit: Optional[str] = None
    chapter: Optional[str] = None  # Legacy support
    concept: Optional[str] = None  # Legacy support
    
    # Templates
    template: Optional[str] = None  # Primary template
    template_variants: List[str] = []
    
    # Variables
    variables: Dict[str, Union[VariableConfig, Dict[str, Any]]] = {}
    
    # Constraints
    constraints: Constraints = Constraints()
    
    # Formula and solution
    formula: Optional[str] = None
    answer_unit: str = "dimensionless"
    answer_type: AnswerType = AnswerType.NUMERICAL  # Determines option generation strategy
    answer_options: Optional[List[str]] = None  # REQUIRED for categorical/boolean types
    solution_template: Optional[str] = None
    
    # Difficulty
    difficulty_level: DifficultyLevel = DifficultyLevel.EASY
    difficulty_factors: List[str] = []
    
    # Options
    options: Optional[OptionsConfig] = None
    
    # Metadata
    tags: List[str] = []
    source_reference: Optional[SourceReference] = None
    question_type: Optional[str] = None  # formula_based, identity_recall, etc.
    
    @validator('exam', pre=True, always=True)
    def normalize_exam(cls, v):
        if v:
            return v.lower().strip().replace(" ", "_")
        return "ts_eamcet"

    @validator('template_variants', pre=True, always=True)
    def ensure_templates(cls, v, values):
        if not v and values.get('template'):
            return [values['template']]
        return v or []
    
    @validator('answer_options', always=True)
    def validate_answer_options(cls, v, values):
        """Ensure categorical/boolean types have answer_options defined."""
        answer_type = values.get('answer_type')
        if answer_type in [AnswerType.CATEGORICAL, AnswerType.BOOLEAN, 'categorical', 'boolean']:
            if not v or len(v) < 2:
                raise ValueError(
                    f"Blueprint with answer_type='{answer_type}' MUST have at least 2 answer_options defined"
                )
            if len(v) < 4:
                # Warning but don't fail - will be caught at generation time
                pass
        return v
    
    @validator('formula', always=True)
    def validate_formula(cls, v, values):
        """Ensure numerical types have formula defined."""
        answer_type = values.get('answer_type')
        if answer_type in [AnswerType.NUMERICAL, 'numerical', 'numeric']:
            if not v and not values.get('answer_options'):
                # Either formula OR answer_options must exist for numerical
                pass  # Allow for now, generator will use fallback
        return v
    
    class Config:
        use_enum_values = True


class GeneratedQuestion(BaseModel):
    """A question generated from a blueprint"""
    id: Optional[str] = None
    blueprint_id: str
    question_text: str
    options: List[str]
    correct_answer: str
    correct_option_index: int
    solution: Optional[str] = None
    
    # Metadata
    subject: str
    chapter: Optional[str] = None
    concept: Optional[str] = None
    difficulty: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    expected_time_sec: int = 60
    tags: List[str] = []
    
    # Variable values used
    variable_values: Dict[str, Any] = {}
    variables_used: Dict[str, Any] = {}
    
    # Timestamp
    generated_at: Optional[Any] = None
