"""
Repository layer for database operations.

This module provides high-level database operations for lessons, files,
and progress tracking with a clean interface for the web API.
"""

import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from .models import Lesson, LessonFile, GenerationProgress


class LessonRepository:
    """Repository for lesson CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_lesson(
        self,
        lesson_id: str,
        topics: List[str],
        generation_config: Optional[Dict[str, Any]] = None,
        ai_model: Optional[str] = None,
    ) -> Lesson:
        """Create a new lesson record."""
        
        lesson = Lesson(
            lesson_id=lesson_id,
            status="pending",
            topics=topics,
            total_topics=len(topics),
            generation_config=generation_config,
            ai_model=ai_model,
        )
        
        self.db.add(lesson)
        self.db.commit()
        self.db.refresh(lesson)
        
        return lesson
    
    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """Get a lesson by ID."""
        return self.db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    
    def update_lesson_status(
        self,
        lesson_id: str,
        status: str,
        progress_percentage: Optional[float] = None,
        current_step: Optional[str] = None,
        topics_completed: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update lesson status and progress."""
        
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return False
        
        lesson.status = status
        lesson.updated_at = datetime.now()
        
        if progress_percentage is not None:
            lesson.progress_percentage = progress_percentage
        
        if current_step is not None:
            lesson.current_step = current_step
        
        if topics_completed is not None:
            lesson.topics_completed = topics_completed
        
        if error_message is not None:
            lesson.error_message = error_message
        
        self.db.commit()
        return True
    
    def list_lessons(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Lesson], int]:
        """List lessons with optional filtering and pagination."""
        
        query = self.db.query(Lesson)
        
        if status:
            query = query.filter(Lesson.status == status)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        lessons = (
            query.order_by(desc(Lesson.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return lessons, total_count
    
    def delete_lesson(self, lesson_id: str) -> bool:
        """Delete a lesson and all associated data."""
        
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return False
        
        self.db.delete(lesson)
        self.db.commit()
        
        return True
    
    def update_file_statistics(self, lesson_id: str) -> bool:
        """Update file count and total size for a lesson."""
        
        lesson = self.get_lesson(lesson_id)
        if not lesson:
            return False
        
        # Calculate statistics from associated files
        file_stats = (
            self.db.query(
                func.count(LessonFile.file_id).label('total_files'),
                func.sum(LessonFile.file_size).label('total_size')
            )
            .filter(LessonFile.lesson_id == lesson_id)
            .first()
        )
        
        lesson.total_files = file_stats.total_files or 0
        lesson.total_size = file_stats.total_size or 0
        
        self.db.commit()
        return True


class FileRepository:
    """Repository for lesson file operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def store_file(
        self,
        lesson_id: str,
        file_path: str,
        file_content: bytes,
        compress: bool = True,
    ) -> LessonFile:
        """Store a file in the database."""
        
        path_obj = Path(file_path)
        file_name = path_obj.name
        file_type = path_obj.suffix.lstrip('.')
        
        # Compress content if requested (for text files)
        if compress and file_type in ['py', 'md', 'txt', 'json', 'yml', 'yaml']:
            file_content = gzip.compress(file_content)
        
        # Determine content type
        content_type_map = {
            'py': 'text/x-python',
            'md': 'text/markdown',
            'txt': 'text/plain',
            'json': 'application/json',
            'yml': 'text/yaml',
            'yaml': 'text/yaml',
        }
        content_type = content_type_map.get(file_type, 'application/octet-stream')
        
        lesson_file = LessonFile(
            lesson_id=lesson_id,
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            content_type=content_type,
            file_size=len(file_content),
            file_content=file_content,
        )
        
        self.db.add(lesson_file)
        self.db.commit()
        self.db.refresh(lesson_file)
        
        return lesson_file
    
    def get_file(self, file_id: int) -> Optional[LessonFile]:
        """Get a file by ID."""
        return self.db.query(LessonFile).filter(LessonFile.file_id == file_id).first()
    
    def get_lesson_files(self, lesson_id: str) -> List[LessonFile]:
        """Get all files for a lesson."""
        return (
            self.db.query(LessonFile)
            .filter(LessonFile.lesson_id == lesson_id)
            .order_by(LessonFile.file_path)
            .all()
        )
    
    def get_file_content(self, file_id: int, decompress: bool = True) -> Optional[bytes]:
        """Get file content, optionally decompressing it."""
        
        file_record = self.get_file(file_id)
        if not file_record:
            return None
        
        content = file_record.file_content
        
        # Decompress if it's a compressed text file
        if decompress and file_record.file_type in ['py', 'md', 'txt', 'json', 'yml', 'yaml']:
            try:
                content = gzip.decompress(content)
            except gzip.BadGzipFile:
                # File wasn't compressed, return as-is
                pass
        
        return content
    
    def delete_lesson_files(self, lesson_id: str) -> int:
        """Delete all files for a lesson."""
        
        deleted_count = (
            self.db.query(LessonFile)
            .filter(LessonFile.lesson_id == lesson_id)
            .delete()
        )
        
        self.db.commit()
        return deleted_count
    
    def bulk_store_files(
        self,
        lesson_id: str,
        files: List[Tuple[str, bytes]],
        compress: bool = True,
    ) -> List[LessonFile]:
        """Store multiple files efficiently."""
        
        lesson_files = []
        
        for file_path, file_content in files:
            path_obj = Path(file_path)
            file_name = path_obj.name
            file_type = path_obj.suffix.lstrip('.')
            
            # Compress content if requested
            if compress and file_type in ['py', 'md', 'txt', 'json', 'yml', 'yaml']:
                file_content = gzip.compress(file_content)
            
            content_type_map = {
                'py': 'text/x-python',
                'md': 'text/markdown',
                'txt': 'text/plain',
                'json': 'application/json',
                'yml': 'text/yaml',
                'yaml': 'text/yaml',
            }
            content_type = content_type_map.get(file_type, 'application/octet-stream')
            
            lesson_file = LessonFile(
                lesson_id=lesson_id,
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                content_type=content_type,
                file_size=len(file_content),
                file_content=file_content,
            )
            
            lesson_files.append(lesson_file)
        
        # Bulk insert
        self.db.add_all(lesson_files)
        self.db.commit()
        
        return lesson_files


class ProgressRepository:
    """Repository for progress tracking operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_step(
        self,
        lesson_id: str,
        module_name: str,
        step_name: str,
        step_metadata: Optional[Dict[str, Any]] = None,
    ) -> GenerationProgress:
        """Record the start of a generation step."""
        
        progress = GenerationProgress(
            lesson_id=lesson_id,
            module_name=module_name,
            step_name=step_name,
            status="started",
            step_metadata=step_metadata,
        )
        
        self.db.add(progress)
        self.db.commit()
        self.db.refresh(progress)
        
        return progress
    
    def complete_step(
        self,
        progress_id: int,
        step_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a step as completed."""
        
        progress = self.db.query(GenerationProgress).filter(
            GenerationProgress.progress_id == progress_id
        ).first()
        
        if not progress:
            return False
        
        progress.status = "completed"
        progress.completed_at = datetime.now()
        
        if step_metadata:
            progress.step_metadata = {**(progress.step_metadata or {}), **step_metadata}
        
        self.db.commit()
        return True
    
    def fail_step(
        self,
        progress_id: int,
        error_message: str,
        step_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Mark a step as failed."""
        
        progress = self.db.query(GenerationProgress).filter(
            GenerationProgress.progress_id == progress_id
        ).first()
        
        if not progress:
            return False
        
        progress.status = "failed"
        progress.completed_at = datetime.now()
        progress.error_message = error_message
        
        if step_metadata:
            progress.step_metadata = {**(progress.step_metadata or {}), **step_metadata}
        
        self.db.commit()
        return True
    
    def get_lesson_progress(self, lesson_id: str) -> List[GenerationProgress]:
        """Get all progress entries for a lesson."""
        
        return (
            self.db.query(GenerationProgress)
            .filter(GenerationProgress.lesson_id == lesson_id)
            .order_by(GenerationProgress.started_at)
            .all()
        )
    
    def get_progress_summary(self, lesson_id: str) -> Dict[str, Any]:
        """Get a summary of progress for a lesson."""
        
        progress_entries = self.get_lesson_progress(lesson_id)
        
        total_steps = len(progress_entries)
        completed_steps = sum(1 for p in progress_entries if p.status == "completed")
        failed_steps = sum(1 for p in progress_entries if p.status == "failed")
        in_progress_steps = sum(1 for p in progress_entries if p.status == "started")
        
        # Calculate total duration for completed steps
        total_duration = 0
        for progress in progress_entries:
            if progress.duration_seconds:
                total_duration += progress.duration_seconds
        
        return {
            "lesson_id": lesson_id,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "in_progress_steps": in_progress_steps,
            "success_rate": completed_steps / total_steps if total_steps > 0 else 0,
            "total_duration_seconds": total_duration,
            "average_step_duration": total_duration / completed_steps if completed_steps > 0 else 0,
        }