"""
Configuration management API endpoints.

This module provides endpoints for topic validation, template management,
and configuration options.
"""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..models import (
    TopicValidationRequest,
    TopicValidationResponse,
    TemplateInfo,
    TemplateListResponse,
)
from ...utils.validation import validate_topic
from ...models import TopicConfig


router = APIRouter()


@router.post("/validate-topic", response_model=TopicValidationResponse)
async def validate_topic_config(request: TopicValidationRequest):
    """
    Validate a topic configuration against the schema.
    
    Returns validation results with errors, warnings, and suggestions.
    """
    
    try:
        # Use the existing validation function
        validation_result = validate_topic(request.topic_config)
        
        return TopicValidationResponse(
            is_valid=validation_result.is_valid,
            errors=validation_result.errors,
            warnings=validation_result.warnings, 
            suggestions=validation_result.suggestions,
        )
        
    except Exception as e:
        return TopicValidationResponse(
            is_valid=False,
            errors=[f"Validation error: {str(e)}"],
            warnings=[],
            suggestions=[],
        )


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates():
    """
    List all available templates (built-in and custom).
    """
    
    templates = []
    
    # Add built-in templates
    builtin_templates = [
        TemplateInfo(
            id="learning_path",
            name="Learning Path",
            description="Main learning content template",
            type="learning_path",
            is_custom=False,
        ),
        TemplateInfo(
            id="assignment",
            name="Assignment",
            description="Programming assignment template",
            type="assignment", 
            is_custom=False,
        ),
        TemplateInfo(
            id="starter_example",
            name="Starter Example",
            description="Example code template",
            type="starter_example",
            is_custom=False,
        ),
        TemplateInfo(
            id="test_template",
            name="Test Template", 
            description="Unit test template",
            type="test",
            is_custom=False,
        ),
    ]
    
    templates.extend(builtin_templates)
    
    # TODO: Add custom templates from filesystem
    # custom_template_dir = Path("custom_templates")
    # if custom_template_dir.exists():
    #     for template_file in custom_template_dir.glob("*.j2"):
    #         # Load and parse custom templates
    #         pass
    
    return TemplateListResponse(
        templates=templates,
        total_count=len(templates),
    )


@router.post("/templates")
async def upload_template(
    file: UploadFile = File(...),
    template_type: str = "custom",
    name: Optional[str] = None,
):
    """
    Upload a custom Jinja2 template.
    """
    
    if not file.filename.endswith('.j2'):
        raise HTTPException(
            status_code=400, 
            detail="Template file must have .j2 extension"
        )
    
    # TODO: Implement template upload and validation
    # - Save to custom_templates directory
    # - Validate Jinja2 syntax
    # - Add to template registry
    
    return {
        "message": f"Template '{file.filename}' uploaded successfully",
        "template_id": file.filename.replace('.j2', ''),
        "type": template_type,
    }


@router.get("/defaults")
async def get_default_config():
    """
    Get default configuration options and example topics.
    """
    
    # Load default topics from config
    default_topics_file = Path("config/default_topics.json")
    default_topics = []
    
    if default_topics_file.exists():
        import json
        try:
            with open(default_topics_file) as f:
                default_topics = json.load(f)
        except Exception:
            pass
    
    return {
        "default_difficulty": "intermediate",
        "default_modules": None,
        "supported_difficulties": ["beginner", "intermediate", "advanced"],
        "sample_topics": default_topics,
        "max_concurrent_generations": 5,
        "default_config": {
            "output_dir": "/tmp/generated_lessons",
            "num_modules": None,
            "use_ai": True,
            "difficulty": "intermediate",
            "include_tests": True,
            "include_assignments": True,
        },
    }