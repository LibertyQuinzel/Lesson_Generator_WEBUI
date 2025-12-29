"""
Database-powered task manager for lesson generation.

This module replaces the file-based TaskManager with a database-backed
version that provides better persistence, scalability, and reliability.
"""

import asyncio
import json
import zipfile
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..models import LessonGenerationStatus, GenerationStatus
from ...models import GenerationConfig
from ...database import (
    SessionLocal,
    LessonRepository,
    FileRepository,
    ProgressRepository,
)
from ...database.models import LessonFile


class DatabaseTaskManager:
    """
    Database-powered task manager for lesson generation.
    
    This class provides the same interface as the original TaskManager
    but stores all data in a relational database instead of memory and files.
    """
    
    def __init__(self):
        # No in-memory storage needed - everything goes to database
        pass
    
    async def create_task(
        self,
        lesson_id: str,
        topics: List[str],
        config: GenerationConfig,
        template_ids: Optional[List[str]] = None,
    ) -> LessonGenerationStatus:
        """Create a new lesson generation task in database."""
        
        # Convert config to dictionary for storage
        config_dict = {
            "output_dir": str(config.output_dir),
            "modules_count": config.modules_count,
            "difficulty": config.difficulty,
            "use_ai": config.use_ai,
            "strict_ai": config.strict_ai,
            "workers": config.workers,
            "openai_api_key": bool(config.openai_api_key) if config.openai_api_key else False,
            "openai_model": config.openai_model,
            "openai_organization": config.openai_organization,
            "request_timeout": config.request_timeout,
            "rate_limit_delay": config.rate_limit_delay,
            "custom_templates_dir": str(config.custom_templates_dir) if config.custom_templates_dir else None,
            "reference_lesson_dir": str(config.reference_lesson_dir) if config.reference_lesson_dir else None,
            "enable_cache": config.enable_cache,
            "verbose": config.verbose,
        }
        
        # Use synchronous database operations for now (we'll improve this later)
        from ...database import SessionLocal
        
        db = SessionLocal()
        try:
            repo = LessonRepository(db)
            
            # Create lesson record
            lesson = repo.create_lesson(
                lesson_id=lesson_id,
                topics=topics,
                generation_config=config_dict,
                ai_model=config.openai_model,
            )
            
            # Convert to API format
            status = LessonGenerationStatus(
                lesson_id=lesson_id,
                status=GenerationStatus.PENDING,
                created_at=lesson.created_at,
                updated_at=lesson.updated_at,
                topics=topics,
                progress={
                    "percentage": 0.0,
                    "current_step": "Initializing...",
                    "topics_completed": 0,
                    "total_topics": len(topics),
                    "template_ids": template_ids,
                },
            )
            
            return status
        finally:
            db.close()
    
    async def get_task_status(self, lesson_id: str) -> Optional[LessonGenerationStatus]:
        """Get the current status of a task from database."""
        
        from ...database import SessionLocal
        
        db = SessionLocal()
        try:
            repo = LessonRepository(db)
            lesson = repo.get_lesson(lesson_id)
            
            if not lesson:
                return None
            
            # Convert database model to API format
            return LessonGenerationStatus(
                lesson_id=lesson.lesson_id,
                status=self._convert_db_status(lesson.status),
                created_at=lesson.created_at,
                updated_at=lesson.updated_at,
                topics=lesson.topics,
                progress={
                    "percentage": lesson.progress_percentage,
                    "current_step": lesson.current_step,
                    "topics_completed": lesson.topics_completed,
                    "total_topics": lesson.total_topics,
                    "template_ids": None,  # Not stored in this version
                },
                error_message=lesson.error_message,
                result_files=None,  # Calculated on demand
                download_url=f"/api/v1/lessons/{lesson_id}/download" if lesson.status == "completed" else None,
                zip_file_path=None,  # Generated on demand
            )
        finally:
            db.close()
    
    async def update_task_status(
        self,
        lesson_id: str,
        status: GenerationStatus,
        message: str = "",
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
        download_url: Optional[str] = None,
        result_files: Optional[List[str]] = None,
        zip_file_path: Optional[str] = None,
    ) -> bool:
        """Update the status of a task in database."""
        
        db = SessionLocal()
        try:
            repo = LessonRepository(db)
            
            return repo.update_lesson_status(
                lesson_id=lesson_id,
                status=self._convert_api_status(status),
                progress_percentage=progress,
                current_step=message if message else None,
                error_message=error_message,
            )
        finally:
            db.close()
    
    async def list_tasks(
        self, 
        status: Optional[GenerationStatus] = None,
        limit: int = 50,
    ) -> List[LessonGenerationStatus]:
        """List tasks from database, optionally filtered by status."""
        
        db = SessionLocal()
        try:
            repo = LessonRepository(db)
            
            db_status = self._convert_api_status(status) if status else None
            lessons, _ = repo.list_lessons(status=db_status, limit=limit)
            
            # Convert to API format
            result = []
            for lesson in lessons:
                api_status = LessonGenerationStatus(
                    lesson_id=lesson.lesson_id,
                    status=self._convert_db_status(lesson.status),
                    created_at=lesson.created_at,
                    updated_at=lesson.updated_at,
                    topics=lesson.topics,
                    progress={
                        "percentage": lesson.progress_percentage,
                        "current_step": lesson.current_step,
                        "topics_completed": lesson.topics_completed,
                        "total_topics": lesson.total_topics,
                        "template_ids": None,
                    },
                    error_message=lesson.error_message,
                    download_url=f"/api/v1/lessons/{lesson.lesson_id}/download" if lesson.status == "completed" else None,
                )
                result.append(api_status)
            
            return result
        finally:
            db.close()
    
    async def store_lesson_files(
        self, 
        lesson_id: str,
        lesson_results: List[Any],
    ) -> bool:
        """
        Store generated lesson files in the database.
        
        Args:
            lesson_id: The lesson generation task ID
            lesson_results: List of lesson generation results
            
        Returns:
            bool: True if storage was successful
        """
        
        db = SessionLocal()
        try:
            file_repo = FileRepository(db)
            lesson_repo = LessonRepository(db)
            
            files_to_store = []
            
            # Extract files from lesson results
            print(f"🔧 DEBUG: Processing {len(lesson_results)} lesson results")
            for result in lesson_results:
                print(f"🔧 DEBUG: Result type: {type(result)}")
                
                # Handle LessonGenerationResult objects that contain GeneratedFile objects
                if hasattr(result, 'modules'):
                    print(f"🔧 DEBUG: Found {len(result.modules)} modules")
                    for module in result.modules:
                        if hasattr(module, 'files'):
                            for generated_file in module.files:
                                try:
                                    rel_path = str(generated_file.path.relative_to(generated_file.path.parents[1]))
                                    content = generated_file.content.encode('utf-8') if isinstance(generated_file.content, str) else generated_file.content
                                    files_to_store.append((rel_path, content))
                                    print(f"🔧 DEBUG: Added module file: {rel_path}")
                                except Exception as e:
                                    print(f"❌ Failed to process module file {generated_file.path}: {e}")
                
                # Handle config files
                if hasattr(result, 'config_files'):
                    print(f"🔧 DEBUG: Found {len(result.config_files)} config files")
                    for config_file in result.config_files:
                        try:
                            rel_path = str(config_file.path.relative_to(config_file.path.parents[1]))
                            content = config_file.content.encode('utf-8') if isinstance(config_file.content, str) else config_file.content
                            files_to_store.append((rel_path, content))
                            print(f"🔧 DEBUG: Added config file: {rel_path}")
                        except Exception as e:
                            print(f"❌ Failed to process config file {config_file.path}: {e}")
                
                # Fallback: try filesystem approach
                if hasattr(result, 'output_dir') and result.output_dir:
                    output_path = Path(result.output_dir)
                    if output_path.exists():
                        for file_path in output_path.rglob('*'):
                            if file_path.is_file():
                                # Read file content
                                try:
                                    with open(file_path, 'rb') as f:
                                        content = f.read()
                                    
                                    # Calculate relative path for storage
                                    rel_path = file_path.relative_to(output_path.parent)
                                    files_to_store.append((str(rel_path), content))
                                    print(f"🔧 DEBUG: Added filesystem file: {rel_path}")
                                    
                                except Exception as e:
                                    print(f"❌ Failed to read file {file_path}: {e}")
                                    continue
            
            # Bulk store files
            if files_to_store:
                print(f"🔧 DEBUG: Calling bulk_store_files with {len(files_to_store)} files")
                try:
                    file_repo.bulk_store_files(lesson_id, files_to_store)
                    print(f"✅ Bulk storage completed for lesson {lesson_id}")
                    
                    # Update lesson statistics
                    lesson_repo.update_file_statistics(lesson_id)
                    print(f"✅ Updated statistics for lesson {lesson_id}")
                    
                    # Verify storage by counting files
                    file_count = db.query(LessonFile).filter_by(lesson_id=lesson_id).count()
                    print(f"🔧 DEBUG: Database now contains {file_count} files for lesson {lesson_id}")
                    
                except Exception as e:
                    print(f"❌ Failed to store files in database: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print(f"⚠️ No files found to store for lesson {lesson_id}")
            
            return True
        finally:
            db.close()
    
    async def create_lesson_archive(
        self, 
        lesson_id: str,
    ) -> bytes:
        """
        Create a ZIP archive of generated lesson files from database.
        
        Args:
            lesson_id: The lesson generation task ID
            
        Returns:
            bytes: ZIP file content
        """
        
        db = SessionLocal()
        try:
            file_repo = FileRepository(db)
            lesson_repo = LessonRepository(db)
            
            lesson = lesson_repo.get_lesson(lesson_id)
            if not lesson:
                raise ValueError(f"Lesson {lesson_id} not found")
            
            lesson_files = file_repo.get_lesson_files(lesson_id)
            
            # Create ZIP in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add each file to the ZIP
                for lesson_file in lesson_files:
                    content = file_repo.get_file_content(lesson_file.file_id)
                    if content:
                        zipf.writestr(lesson_file.file_path, content)
                
                # Add a summary file
                summary = {
                    "lesson_id": lesson_id,
                    "generated_at": lesson.created_at.isoformat(),
                    "topics": lesson.topics,
                    "total_files": lesson.total_files,
                    "total_size": lesson.total_size,
                    "status": lesson.status,
                }
                
                zipf.writestr(
                    "generation_summary.json",
                    json.dumps(summary, indent=2),
                )
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
        finally:
            db.close()
    
    async def cleanup_task(self, lesson_id: str) -> bool:
        """
        Clean up a task and associated files from database.
        
        Args:
            lesson_id: The lesson generation task ID
            
        Returns:
            True if cleanup was successful, False if task not found
        """
        
        db = SessionLocal()
        try:
            repo = LessonRepository(db)
            return repo.delete_lesson(lesson_id)
        finally:
            db.close()
    
    async def cleanup(self):
        """Clean up method for compatibility - database handles persistence."""
        # Database handles cleanup automatically, nothing to do here
        pass
    
    def _convert_db_status(self, db_status: str) -> GenerationStatus:
        """Convert database status to API status enum."""
        status_map = {
            "pending": GenerationStatus.PENDING,
            "processing": GenerationStatus.PROCESSING, 
            "completed": GenerationStatus.COMPLETED,
            "failed": GenerationStatus.FAILED,
            "error": GenerationStatus.FAILED,
        }
        return status_map.get(db_status, GenerationStatus.FAILED)
    
    def _convert_api_status(self, api_status: GenerationStatus) -> str:
        """Convert API status enum to database status string."""
        if api_status is None:
            return None
            
        status_map = {
            GenerationStatus.PENDING: "pending",
            GenerationStatus.PROCESSING: "processing",
            GenerationStatus.COMPLETED: "completed",
            GenerationStatus.FAILED: "failed",
        }
        return status_map.get(api_status, "failed")


# Singleton instance for dependency injection
_database_task_manager_instance = None


def get_database_task_manager() -> DatabaseTaskManager:
    """Get the singleton DatabaseTaskManager instance."""
    global _database_task_manager_instance
    
    if _database_task_manager_instance is None:
        _database_task_manager_instance = DatabaseTaskManager()
    
    return _database_task_manager_instance