"""
Validation utilities for the lesson generator.

This module provides validation functions for topics, configurations,
and generated content to ensure quality and consistency.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List

from ..models import TopicConfig, ValidationResult


def validate_topic(topic: TopicConfig) -> ValidationResult:
    """
    Validate a topic configuration for completeness and correctness.
    
    Args:
        topic: Topic configuration to validate
        
    Returns:
        ValidationResult with any errors, warnings, or suggestions
    """
    errors = []
    warnings = []
    suggestions = []
    
    # Validate topic name
    if not topic.name or len(topic.name.strip()) == 0:
        errors.append("Topic name cannot be empty")
    elif len(topic.name) > 100:
        errors.append("Topic name must be 100 characters or less")
    
    # Validate slug format
    if not topic.slug:
        errors.append("Topic slug cannot be empty")
    elif not re.match(r'^[a-z0-9_]+$', topic.slug):
        errors.append("Topic slug must contain only lowercase letters, numbers, and underscores")
    
    # Validate description
    if not topic.description or len(topic.description.strip()) < 10:
        errors.append("Topic description must be at least 10 characters")
    elif len(topic.description) > 500:
        errors.append("Topic description must be 500 characters or less")
    
    # Validate estimated hours
    if topic.estimated_hours < 0.5:
        errors.append("Estimated hours must be at least 0.5")
    elif topic.estimated_hours > 40:
        errors.append("Estimated hours must be 40 or less")
    elif topic.estimated_hours > 20:
        warnings.append("Topic with more than 20 hours might be too long for a single lesson")
    
    # Validate concepts
    if not topic.concepts or len(topic.concepts) == 0:
        errors.append("At least one concept is required")
    elif len(topic.concepts) > 15:
        warnings.append("More than 15 concepts might make the lesson unfocused")
    
    # Check for empty concepts
    empty_concepts = [i for i, concept in enumerate(topic.concepts) if not concept.strip()]
    if empty_concepts:
        errors.append(f"Empty concepts found at positions: {empty_concepts}")
    
    # Validate learning objectives
    if not topic.learning_objectives or len(topic.learning_objectives) < 2:
        errors.append("At least 2 learning objectives are required")
    elif len(topic.learning_objectives) > 10:
        warnings.append("More than 10 learning objectives might be overwhelming")
    
    # Check learning objectives quality
    for i, objective in enumerate(topic.learning_objectives):
        if len(objective.strip()) < 10:
            warnings.append(f"Learning objective {i+1} is very short - consider adding more detail")
    
    # Validate modules
    if not topic.modules or len(topic.modules) < 1:
        errors.append("At least 1 module is required")
    elif len(topic.modules) > 10:
        warnings.append("More than 10 modules might make the lesson too complex")
    
    # Check module type distribution
    if topic.modules:
        starter_modules = [m for m in topic.modules if m.type == "starter"]
        assignment_modules = [m for m in topic.modules if m.type == "assignment"]
        
        if len(starter_modules) == 0:
            errors.append("At least one starter module is required")
        elif len(starter_modules) > 2:
            warnings.append("More than 2 starter modules might be excessive")
        
        # For single module lessons, don't require assignment modules
        if len(topic.modules) > 1 and len(assignment_modules) == 0:
            errors.append("Multi-module lessons need at least one assignment module")
        
        # Check for duplicate module names
        module_names = [m.name.lower().strip() for m in topic.modules]
        duplicates = set([name for name in module_names if module_names.count(name) > 1])
        if duplicates:
            errors.append(f"Duplicate module names found: {', '.join(duplicates)}")
    
    # Suggestions for improvement
    if topic.difficulty == "beginner" and topic.estimated_hours > 8:
        suggestions.append("Consider breaking down beginner topics into smaller lessons")
    
    if len(topic.prerequisites) == 0 and topic.difficulty != "beginner":
        suggestions.append("Consider adding prerequisites for non-beginner topics")
    
    if len([m for m in topic.modules if m.type == "project"]) == 0:
        suggestions.append("Consider adding a project module for hands-on practice")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions
    )


def validate_output_path(output_path: Path) -> bool:
    """
    Validate that an output path is suitable for lesson generation.
    
    Args:
        output_path: Path to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If path is invalid
    """
    if not isinstance(output_path, Path):
        output_path = Path(output_path)
    
    # Check if path is absolute or can be resolved
    try:
        resolved_path = output_path.resolve()
    except Exception as e:
        raise ValueError(f"Cannot resolve output path: {e}")
    
    # Check if parent directory exists or can be created
    parent = resolved_path.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ValueError(f"No permission to create directory: {parent}")
        except Exception as e:
            raise ValueError(f"Cannot create parent directory: {e}")
    
    # Check if we can write to the location
    if resolved_path.exists():
        if not resolved_path.is_dir():
            raise ValueError(f"Output path exists but is not a directory: {resolved_path}")
        
        # Try to create a test file to check write permissions
        test_file = resolved_path / ".test_write_permission"
        try:
            test_file.touch()
            test_file.unlink()
        except PermissionError:
            raise ValueError(f"No write permission for directory: {resolved_path}")
        except Exception as e:
            raise ValueError(f"Cannot write to directory: {e}")
    
    return True


def validate_topic_name(name: str) -> str:
    """
    Validate and normalize a topic name.
    
    Args:
        name: Raw topic name input
        
    Returns:
        Normalized topic name
        
    Raises:
        ValueError: If name is invalid
    """
    if not name or not name.strip():
        raise ValueError("Topic name cannot be empty")
    
    normalized = name.strip()
    
    if len(normalized) > 100:
        raise ValueError("Topic name must be 100 characters or less")
    
    # Check for invalid characters that might cause issues
    if re.search(r'[<>:"/\\|?*]', normalized):
        raise ValueError("Topic name contains invalid characters")
    
    return normalized


def create_slug_from_name(name: str) -> str:
    """
    Create a URL-safe slug from a topic name.
    
    Args:
        name: Topic name
        
    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    slug = name.lower().strip()
    
    # Replace spaces and common separators with underscores
    slug = re.sub(r'[\s\-\.]+', '_', slug)
    
    # Remove non-alphanumeric characters except underscores
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    
    # Remove multiple consecutive underscores
    slug = re.sub(r'_+', '_', slug)
    
    # Remove leading/trailing underscores
    slug = slug.strip('_')
    
    if not slug:
        raise ValueError("Cannot create valid slug from topic name")
    
    return slug


def validate_json_config(config_path: Path) -> Dict[str, Any]:
    """
    Validate and load a JSON configuration file.
    
    Args:
        config_path: Path to JSON configuration file
        
    Returns:
        Loaded and validated configuration
        
    Raises:
        ValueError: If configuration is invalid
    """
    if not config_path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")
    
    if not config_path.is_file():
        raise ValueError(f"Configuration path is not a file: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise ValueError(f"Cannot read configuration file: {e}")
    
    if not isinstance(config_data, dict):
        raise ValueError("Configuration file must contain a JSON object")
    
    return config_data


def validate_openai_api_key(api_key: str) -> bool:
    """
    Validate the format of an OpenAI API key.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if format appears valid
        
    Raises:
        ValueError: If API key format is invalid
    """
    if not api_key or not api_key.strip():
        raise ValueError("OpenAI API key cannot be empty")
    
    key = api_key.strip()
    
    # OpenAI keys typically start with 'sk-' and are 48+ characters
    if not key.startswith('sk-'):
        raise ValueError("OpenAI API key must start with 'sk-'")
    
    if len(key) < 20:
        raise ValueError("OpenAI API key appears to be too short")
    
    # Check for obviously invalid characters
    if re.search(r'[^a-zA-Z0-9\-]', key):
        raise ValueError("OpenAI API key contains invalid characters")
    
    return True


def validate_difficulty_progression(topics: List[TopicConfig]) -> ValidationResult:
    """
    Validate that a series of topics has appropriate difficulty progression.
    
    Args:
        topics: List of topic configurations
        
    Returns:
        ValidationResult with progression analysis
    """
    if len(topics) <= 1:
        return ValidationResult(is_valid=True)
    
    warnings = []
    suggestions = []
    
    difficulties = [topic.difficulty for topic in topics]
    
    # Check for appropriate progression
    difficulty_order = ["beginner", "intermediate", "advanced"]
    
    # Find any backward progressions
    for i in range(1, len(difficulties)):
        current_idx = difficulty_order.index(difficulties[i])
        previous_idx = difficulty_order.index(difficulties[i-1])
        
        if current_idx < previous_idx - 1:
            warnings.append(
                f"Large difficulty drop from '{difficulties[i-1]}' to '{difficulties[i]}' "
                f"between topics {i} and {i+1}"
            )
    
    # Suggest improvements
    if all(d == "advanced" for d in difficulties):
        suggestions.append("All topics are advanced - consider adding some intermediate topics")
    elif all(d == "beginner" for d in difficulties):
        suggestions.append("All topics are beginner level - consider progression to intermediate")
    
    return ValidationResult(
        is_valid=True,  # Progression warnings don't make the sequence invalid
        warnings=warnings,
        suggestions=suggestions
    )