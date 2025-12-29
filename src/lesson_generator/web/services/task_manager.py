"""
Background task management for lesson generation.

This module handles the lifecycle of lesson generation tasks including
progress tracking, status updates, and file management.
"""

import asyncio
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile
import shutil

from ..models import LessonGenerationStatus, GenerationStatus
from ...models import GenerationConfig


class TaskManager:
    """
    Manages background lesson generation tasks.
    
    This class handles task creation, status tracking, progress updates,
    and cleanup of generated files.
    """
    
    def __init__(self):
        self.tasks: Dict[str, LessonGenerationStatus] = {}
        self.temp_dir = Path(tempfile.gettempdir()) / "lesson_generator"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_task(
        self,
        lesson_id: str,
        topics: List[str],
        config: GenerationConfig,
        template_ids: Optional[List[str]] = None,
    ) -> LessonGenerationStatus:
        """Create a new lesson generation task."""
        
        now = datetime.now()
        
        status = LessonGenerationStatus(
            lesson_id=lesson_id,
            status=GenerationStatus.PENDING,
            created_at=now,
            updated_at=now,
            topics=topics,
            progress={
                "percentage": 0.0,
                "current_step": "Initializing...",
                "topics_completed": 0,
                "total_topics": len(topics),
                "template_ids": template_ids,
            },
        )
        
        self.tasks[lesson_id] = status
        return status
    
    async def get_task_status(self, lesson_id: str) -> Optional[LessonGenerationStatus]:
        """Get the current status of a task."""
        return self.tasks.get(lesson_id)
    
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
    ):
        """Update the status of a task."""
        
        if lesson_id not in self.tasks:
            return False
        
        task = self.tasks[lesson_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if progress is not None:
            task.progress["percentage"] = progress
        
        if message:
            task.progress["current_step"] = message
        
        if error_message:
            task.error_message = error_message
        
        if download_url:
            task.download_url = download_url
        
        if result_files:
            task.result_files = result_files
            
        if zip_file_path:
            task.zip_file_path = zip_file_path
        
        # TODO: Notify WebSocket clients of status update
        
        return True
    
    async def list_tasks(
        self, 
        status: Optional[GenerationStatus] = None,
        limit: int = 50,
    ) -> List[LessonGenerationStatus]:
        """List tasks, optionally filtered by status."""
        
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def create_lesson_archive(
        self, 
        lesson_id: str,
        lesson_results: List[Any],
    ) -> Path:
        """
        Create a ZIP archive of generated lesson files.
        
        Args:
            lesson_id: The lesson generation task ID
            lesson_results: List of lesson generation results
            
        Returns:
            Path to the created ZIP file
        """
        
        # Ensure the main temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a temporary directory for this lesson
        lesson_dir = self.temp_dir / lesson_id
        lesson_dir.mkdir(parents=True, exist_ok=True)
        
        # Create ZIP file
        zip_path = lesson_dir / f"{lesson_id}_lessons.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add each lesson result to the ZIP
            for i, result in enumerate(lesson_results):
                if hasattr(result, 'output_dir') and result.output_dir:
                    # Add all files from the lesson output directory
                    output_path = Path(result.output_dir)
                    if output_path.exists():
                        for file_path in output_path.rglob('*'):
                            if file_path.is_file():
                                # Calculate relative path for ZIP entry
                                rel_path = file_path.relative_to(output_path.parent)
                                zipf.write(file_path, rel_path)
            
            # Add a summary file
            summary = {
                "lesson_id": lesson_id,
                "generated_at": datetime.now().isoformat(),
                "topics": [getattr(r, 'topic', f'topic_{i}') for i, r in enumerate(lesson_results)],
                "total_lessons": len(lesson_results),
                "files_included": len(zipf.namelist()),
            }
            
            zipf.writestr(
                "generation_summary.json",
                json.dumps(summary, indent=2),
            )
        
        return zip_path
    
    async def cleanup_task(self, lesson_id: str) -> bool:
        """
        Clean up a task and associated files.
        
        Args:
            lesson_id: The lesson generation task ID
            
        Returns:
            True if cleanup was successful, False if task not found
        """
        
        if lesson_id not in self.tasks:
            return False
        
        # Remove task from memory
        del self.tasks[lesson_id]
        
        # Clean up files
        lesson_dir = self.temp_dir / lesson_id
        if lesson_dir.exists():
            shutil.rmtree(lesson_dir)
        
        return True
    
    async def cleanup(self):
        """Clean up all tasks and temporary files."""
        
        # Clean up temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        # Clear tasks
        self.tasks.clear()


# Singleton instance for dependency injection
_task_manager_instance = None


def get_task_manager() -> TaskManager:
    """Get the singleton TaskManager instance."""
    global _task_manager_instance
    
    if _task_manager_instance is None:
        _task_manager_instance = TaskManager()
    
    return _task_manager_instance