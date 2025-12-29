"""
Database models for the Lesson Generator.

This module defines SQLAlchemy models for storing lesson data, files,
and generation progress in a relational database.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, 
    LargeBinary, ForeignKey, JSON, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Lesson(Base):
    """
    Main lesson record containing metadata and generation status.
    
    This table stores the core information about each generated lesson
    including topics, status, progress, and configuration details.
    """
    
    __tablename__ = "lessons"
    
    # Primary identification
    lesson_id = Column(String(50), primary_key=True, index=True)
    
    # Status and timing
    status = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Lesson configuration
    topics = Column(JSON, nullable=False)  # List of topic strings
    total_topics = Column(Integer, nullable=False, default=0)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    current_step = Column(Text)
    topics_completed = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    
    # Generation metadata
    generation_config = Column(JSON)  # Serialized GenerationConfig
    ai_model = Column(String(50))
    
    # File statistics
    total_files = Column(Integer, default=0)
    total_size = Column(Integer, default=0)  # Size in bytes
    
    # Relationships
    files = relationship("LessonFile", back_populates="lesson", cascade="all, delete-orphan")
    progress_entries = relationship("GenerationProgress", back_populates="lesson", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lesson to dictionary for API responses."""
        return {
            "lesson_id": self.lesson_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "topics": self.topics,
            "progress": {
                "percentage": self.progress_percentage,
                "current_step": self.current_step,
                "topics_completed": self.topics_completed,
                "total_topics": self.total_topics,
            },
            "error_message": self.error_message,
            "total_files": self.total_files,
            "total_size": self.total_size,
            "generation_config": self.generation_config,
            "ai_model": self.ai_model,
        }


class LessonFile(Base):
    """
    Individual files generated as part of a lesson.
    
    This table stores the actual file content as binary blobs along with
    metadata like path, size, and content type for efficient retrieval.
    """
    
    __tablename__ = "lesson_files"
    
    # Primary key
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to lesson
    lesson_id = Column(String(50), ForeignKey("lessons.lesson_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File metadata
    file_path = Column(String(500), nullable=False, index=True)  # Relative path within lesson
    file_name = Column(String(255), nullable=False, index=True)
    file_type = Column(String(50), nullable=False, index=True)  # py, md, txt, etc.
    content_type = Column(String(100))  # MIME type
    file_size = Column(Integer, nullable=False)
    
    # File content (stored as compressed binary)
    file_content = Column(LargeBinary, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    lesson = relationship("Lesson", back_populates="files")
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert file to dictionary for API responses."""
        result = {
            "file_id": self.file_id,
            "lesson_id": self.lesson_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_content and self.file_content:
            # Decode binary content to string (assuming UTF-8 text files)
            try:
                result["content"] = self.file_content.decode('utf-8')
            except UnicodeDecodeError:
                # For binary files, provide base64 encoding
                import base64
                result["content"] = base64.b64encode(self.file_content).decode('ascii')
                result["encoding"] = "base64"
        
        return result


class GenerationProgress(Base):
    """
    Detailed progress tracking for lesson generation steps.
    
    This table provides granular tracking of each step in the lesson
    generation process, enabling detailed progress reporting and debugging.
    """
    
    __tablename__ = "generation_progress"
    
    # Primary key
    progress_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to lesson
    lesson_id = Column(String(50), ForeignKey("lessons.lesson_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Progress details
    module_name = Column(String(255), nullable=False, index=True)
    step_name = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # started, completed, failed
    
    # Timing
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime)
    
    # Error information
    error_message = Column(Text)
    
    # Additional metadata
    step_metadata = Column(JSON)  # Additional step-specific data
    
    # Relationships
    lesson = relationship("Lesson", back_populates="progress_entries")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress entry to dictionary for API responses."""
        return {
            "progress_id": self.progress_id,
            "lesson_id": self.lesson_id,
            "module_name": self.module_name,
            "step_name": self.step_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "step_metadata": self.step_metadata,
        }
        
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration of this step in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None