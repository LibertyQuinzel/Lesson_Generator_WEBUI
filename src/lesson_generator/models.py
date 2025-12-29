"""
Data models for the lesson generator.

This module defines Pydantic models for configuration, topics, and generation results.
All models include validation and serialization capabilities.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, validator


class DifficultyLevel(str, Enum):
    """Enumeration for difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ModuleType(str, Enum):
    """Enumeration for module types."""
    STARTER = "starter"
    ASSIGNMENT = "assignment"  
    PROJECT = "project"
    EXTRA = "extra"


class CodeComplexity(str, Enum):
    """Enumeration for code complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class ModuleConfig(BaseModel):
    """Configuration for a single module within a topic."""
    
    name: str = Field(..., min_length=1, max_length=100)
    type: ModuleType
    focus_areas: List[str] = Field(..., min_items=1, max_items=5)
    code_complexity: CodeComplexity
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize module name."""
        if not v.strip():
            raise ValueError("Module name cannot be empty")
        return v.strip()
    
    @validator('focus_areas')
    def validate_focus_areas(cls, v):
        """Validate focus areas list."""
        if not v:
            raise ValueError("At least one focus area is required")
        return [area.strip() for area in v if area.strip()]


class TopicConfig(BaseModel):
    """Configuration for a lesson topic."""
    
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., pattern=r'^[a-z0-9_]+$')
    description: str = Field(..., min_length=10, max_length=500)
    difficulty: DifficultyLevel
    estimated_hours: float = Field(..., ge=0.5, le=40)
    concepts: List[str] = Field(..., min_items=1, max_items=15)
    learning_objectives: List[str] = Field(..., min_items=2, max_items=10)
    prerequisites: List[str] = Field(default_factory=list, max_items=10)
    modules: List[ModuleConfig] = Field(..., min_items=1, max_items=10)
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize topic name."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        if not v:
            raise ValueError("Slug cannot be empty")
        return v.lower().strip()
    
    @validator('concepts')
    def validate_concepts(cls, v):
        """Validate concepts list."""
        if not v:
            raise ValueError("At least one concept is required")
        return [concept.strip() for concept in v if concept.strip()]
    
    @validator('learning_objectives')
    def validate_learning_objectives(cls, v):
        """Validate learning objectives."""
        if len(v) < 2:
            raise ValueError("At least 2 learning objectives are required")
        return [obj.strip() for obj in v if obj.strip()]
    
    @validator('modules')
    def validate_modules(cls, v):
        """Validate modules configuration."""
        if not v:
            raise ValueError("At least 1 module is required")
        
        # For single module lessons, only require a starter module
        if len(v) == 1:
            module_types = [module.type for module in v]
            if ModuleType.STARTER not in module_types:
                raise ValueError("Single module lessons must have a starter module")
        else:
            # For multi-module lessons, require both starter and assignment modules
            module_types = [module.type for module in v]
            if ModuleType.STARTER not in module_types:
                raise ValueError("At least one starter module is required")
            if ModuleType.ASSIGNMENT not in module_types:
                raise ValueError("Multi-module lessons need at least one assignment module")
        
        return v


class GenerationConfig(BaseModel):
    """Configuration for the lesson generation process."""
    
    output_dir: Path
    modules_count: Optional[int] = None
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    use_ai: bool = True
    strict_ai: bool = True
    workers: int = Field(default=1, ge=1, le=8)
    custom_templates_dir: Optional[Path] = None
    reference_lesson_dir: Optional[Path] = None
    enable_cache: bool = True
    verbose: bool = False
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_organization: Optional[str] = None
    request_timeout: int = 30
    rate_limit_delay: float = 1.0
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    @validator('output_dir')
    def validate_output_dir(cls, v):
        """Validate output directory."""
        if isinstance(v, str):
            v = Path(v)
        return v.resolve()
    
    @validator('custom_templates_dir')
    def validate_custom_templates_dir(cls, v):
        """Validate custom templates directory."""
        if v is None:
            return v
        if isinstance(v, str):
            v = Path(v)
        if not v.exists():
            raise ValueError(f"Custom templates directory does not exist: {v}")
        return v.resolve()

    @validator('modules_count')
    def validate_modules_count(cls, v):
        """Validate modules_count only when provided."""
        if v is None:
            return v
        if not (1 <= v <= 10):
            raise ValueError("modules_count must be between 1 and 10")
        return v
    
    @validator('reference_lesson_dir')
    def validate_reference_lesson_dir(cls, v):
        """Validate reference lesson directory."""
        if v is None:
            return v
        if isinstance(v, str):
            v = Path(v)
        if not v.exists():
            raise ValueError(f"Reference lesson directory does not exist: {v}")
        return v.resolve()


class GeneratedFile(BaseModel):
    """Represents a generated file."""
    
    path: Path
    content: str
    file_type: str  # 'python', 'markdown', 'text', etc.
    size_bytes: int
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class ModuleGenerationResult(BaseModel):
    """Result of generating a single module."""
    
    module_name: str
    success: bool
    files: List[GeneratedFile] = Field(default_factory=list)
    error: Optional[str] = None
    generation_time_seconds: float = 0.0
    
    @property
    def file_count(self) -> int:
        """Number of files generated."""
        return len(self.files)
    
    @property
    def total_size_bytes(self) -> int:
        """Total size of generated files in bytes."""
        return sum(file.size_bytes for file in self.files)


class LessonGenerationResult(BaseModel):
    """Result of generating an entire lesson."""
    
    topic_name: str
    topic_slug: str
    success: bool
    output_path: Path
    modules: List[ModuleGenerationResult] = Field(default_factory=list)
    config_files: List[GeneratedFile] = Field(default_factory=list)
    error: Optional[str] = None
    generation_time_seconds: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    generator_version: str = "0.1.0"
    ai_model_used: Optional[str] = None
    quality_report: Optional["QualityReport"] = None
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
    
    @property
    def total_modules(self) -> int:
        """Total number of modules."""
        return len(self.modules)
    
    @property
    def successful_modules(self) -> int:
        """Number of successfully generated modules."""
        return sum(1 for module in self.modules if module.success)
    
    @property
    def total_files(self) -> int:
        """Total number of files generated."""
        return sum(module.file_count for module in self.modules) + len(self.config_files)
    
    @property
    def total_size_bytes(self) -> int:
        """Total size of all generated files."""
        modules_size = sum(module.total_size_bytes for module in self.modules)
        config_size = sum(file.size_bytes for file in self.config_files)
        return modules_size + config_size


class ContentGenerationRequest(BaseModel):
    """Request for AI content generation."""
    
    topic: TopicConfig
    module: ModuleConfig
    content_type: str  # 'learning_path', 'starter_example', 'assignment', 'test'
    additional_context: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class ContentGenerationResponse(BaseModel):
    """Response from AI content generation."""
    
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    model_used: str
    tokens_used: int = 0
    generation_time_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of code or content validation."""
    
    file_path: Optional[Path] = None
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class QualityReport(BaseModel):
    """Comprehensive quality report for generated lesson."""
    
    lesson_path: Path
    python_files_valid: bool
    tests_executable: bool
    quality_score: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True