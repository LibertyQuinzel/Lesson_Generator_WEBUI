"""
API response models for the web interface.
"""

from .responses import (
    LessonGenerationResponse,
    LessonGenerationStatus,
    TopicValidationResponse,
    TemplateListResponse,
    SystemHealth,
    ErrorResponse,
)

__all__ = [
    "LessonGenerationResponse",
    "LessonGenerationStatus", 
    "TopicValidationResponse",
    "TemplateListResponse",
    "SystemHealth",
    "ErrorResponse",
]