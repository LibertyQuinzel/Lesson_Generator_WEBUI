"""
Web interface models for API requests and responses.

This module defines Pydantic models specifically for the web interface,
extending the core models for API communication.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Literal

from pydantic import BaseModel, Field

from ...models import TopicConfig, GenerationConfig, ModuleConfig, DifficultyLevel


class GenerationStatus(str, Enum):
    """Status of lesson generation process."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LessonGenerationRequest(BaseModel):
    """Request model for lesson generation API."""
    
    topics: List[str] = Field(default_factory=list, description="List of lesson topics (optional - AI will generate if empty)")
    modules: int = Field(..., ge=1, le=10, description="Number of modules to generate per topic (required)")
    difficulty: str = Field("intermediate", description="Difficulty level (beginner, intermediate, advanced)")
    include_exercises: bool = Field(True, description="Whether to include exercises")
    include_examples: bool = Field(True, description="Whether to include code examples")
    config: Optional[GenerationConfig] = Field(None, description="Generation configuration options")
    template_ids: Optional[List[str]] = Field(None, description="Custom template IDs to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Python Programming Fundamentals",
                "description": "Learn core Python concepts and best practices",
                "modules": ["Variables and Data Types", "Control Flow", "Functions and Scope"],
                "difficulty": "intermediate",
                "include_exercises": True,
                "include_examples": True
            }
        }


class LessonGenerationResponse(BaseModel):
    """Response model for lesson generation API."""
    
    lesson_id: str = Field(..., description="Unique identifier for the generation task")
    status: GenerationStatus = Field(..., description="Current status of the generation")
    message: str = Field(..., description="Human-readable status message")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    progress_percentage: Optional[float] = Field(None, ge=0, le=100, description="Completion percentage")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lesson_id": "lesson_12345",
                "status": "processing",
                "message": "Generating content for python_fundamentals (2/5 modules complete)",
                "estimated_completion": "2023-12-07T15:30:00Z",
                "progress_percentage": 40.0
            }
        }


class LessonGenerationStatus(BaseModel):
    """Detailed status information for lesson generation."""
    
    lesson_id: str
    status: GenerationStatus
    created_at: datetime
    updated_at: datetime
    topics: List[str]
    progress: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    result_files: Optional[List[str]] = Field(None, description="List of generated file paths")
    download_url: Optional[str] = Field(None, description="URL to download generated lessons")
    zip_file_path: Optional[str] = Field(None, description="Internal file path to ZIP file")


class TopicValidationRequest(BaseModel):
    """Request model for topic validation."""
    
    topic_config: TopicConfig = Field(..., description="Topic configuration to validate")
    
    class Config:
        json_schema_extra = {
            "example": {
                "topic_config": {
                    "name": "advanced_python",
                    "difficulty": "advanced",
                    "concepts": ["decorators", "metaclasses", "async/await"],
                    "learning_objectives": ["Understand advanced Python features"],
                    "prerequisites": ["python_fundamentals"],
                    "estimated_hours": 20,
                    "modules": []
                }
            }
        }


class TopicValidationResponse(BaseModel):
    """Response model for topic validation."""
    
    is_valid: bool = Field(..., description="Whether the topic configuration is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")


class TemplateInfo(BaseModel):
    """Information about available templates."""
    
    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template description")
    type: str = Field(..., description="Template type (learning_path, assignment, etc.)")
    is_custom: bool = Field(False, description="Whether this is a custom user template")
    created_at: Optional[datetime] = Field(None, description="Template creation time")


class TemplateListResponse(BaseModel):
    """Response model for template listing."""
    
    templates: List[TemplateInfo] = Field(..., description="List of available templates")
    total_count: int = Field(..., description="Total number of templates")


class SystemHealth(BaseModel):
    """System health check response."""
    
    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="System uptime in seconds") 
    openai_api_available: bool = Field(..., description="Whether OpenAI API is accessible")
    storage_available: bool = Field(..., description="Whether storage is accessible")
    active_generations: int = Field(..., description="Number of active generation tasks")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Invalid topic configuration provided",
                "details": {
                    "field": "modules",
                    "issue": "At least one module is required"
                },
                "timestamp": "2023-12-07T10:30:00Z"
            }
        }


# WebSocket message models

class WebSocketMessageType(str, Enum):
    """WebSocket message types."""
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGE = "status_change"
    ERROR = "error"
    COMPLETION = "completion"


class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""
    
    type: WebSocketMessageType = Field(..., description="Message type")
    lesson_id: str = Field(..., description="Lesson generation ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message payload")


class ProgressUpdateMessage(WebSocketMessage):
    """WebSocket progress update message."""
    
    type: Literal[WebSocketMessageType.PROGRESS_UPDATE] = WebSocketMessageType.PROGRESS_UPDATE
    progress_percentage: float = Field(..., ge=0, le=100, description="Current progress percentage")
    current_step: str = Field(..., description="Current generation step")
    message: str = Field(..., description="Human-readable progress message")


class StatusChangeMessage(WebSocketMessage):
    """WebSocket status change message."""
    
    type: Literal[WebSocketMessageType.STATUS_CHANGE] = WebSocketMessageType.STATUS_CHANGE
    old_status: GenerationStatus = Field(..., description="Previous status")
    new_status: GenerationStatus = Field(..., description="New status")
    message: str = Field(..., description="Status change message")


class CompletionMessage(WebSocketMessage):
    """WebSocket completion message."""
    
    type: Literal[WebSocketMessageType.COMPLETION] = WebSocketMessageType.COMPLETION
    download_url: str = Field(..., description="URL to download generated lessons")
    result_summary: Dict[str, Any] = Field(..., description="Generation result summary")