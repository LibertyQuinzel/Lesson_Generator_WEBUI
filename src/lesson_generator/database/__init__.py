"""
Database layer for the Lesson Generator.

This module provides database models, schemas, and connection management
for storing lesson generation data, progress tracking, and file storage.
"""

# Import order matters for SQLAlchemy models
from .models import Base, Lesson, LessonFile, GenerationProgress
from .database import (
    engine, 
    async_engine,
    SessionLocal, 
    AsyncSessionLocal,
    get_database, 
    get_async_database,
    init_database,
    async_init_database,
    check_database_health,
    async_check_database_health,
    reset_database,
    async_reset_database,
)
from .repositories import LessonRepository, FileRepository, ProgressRepository

__all__ = [
    # Models
    "Base",
    "Lesson",
    "LessonFile", 
    "GenerationProgress",
    # Database engines and sessions
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_database",
    "get_async_database",
    # Initialization functions
    "init_database",
    "async_init_database",
    "check_database_health", 
    "async_check_database_health",
    "reset_database",
    "async_reset_database",
    # Repositories
    "LessonRepository",
    "FileRepository",
    "ProgressRepository",
]