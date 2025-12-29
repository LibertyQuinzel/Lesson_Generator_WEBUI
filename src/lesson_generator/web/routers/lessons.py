"""
Lesson generation API endpoints.

This module provides endpoints for lesson generation, status tracking,
and result retrieval.
"""

import uuid
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse, Response

from ..models import (
    LessonGenerationRequest,
    LessonGenerationResponse, 
    LessonGenerationStatus,
    GenerationStatus,
)
from ..services.database_task_manager import get_database_task_manager
from ..services.websocket import get_websocket_manager
from ...core import LessonGenerator
from ...models import GenerationConfig, DifficultyLevel
from ...cli import create_topic_from_name
from ...content import OPENAI_CLIENT_TYPE


router = APIRouter()


@router.post("/{lesson_id}/recover")
async def recover_lesson(
    lesson_id: str,
    task_manager = Depends(get_database_task_manager),
):
    """Recover a lesson that exists on filesystem but not in memory (after server restart)."""
    
    from datetime import datetime
    
    # Check if lesson directory exists
    lesson_dir = Path("generated_lessons") / lesson_id
    if not lesson_dir.exists():
        raise HTTPException(status_code=404, detail="Lesson not found on filesystem")
    
    # Collect all files in the lesson directory
    result_files = []
    for file_path in lesson_dir.rglob('*'):
        if file_path.is_file():
            result_files.append(str(file_path))
    
    if not result_files:
        raise HTTPException(status_code=404, detail="No files found in lesson directory")
    
    # Create ZIP file for download
    import zipfile
    import tempfile
    
    temp_dir = Path(tempfile.gettempdir()) / "lesson_generator" / lesson_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / f"{lesson_id}_lessons.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in result_files:
            rel_path = Path(file_path).relative_to(lesson_dir.parent)
            zipf.write(file_path, rel_path)
    
    # Infer topics from directory structure
    topics = []
    for item in lesson_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            topics.append(item.name)
    
        # Create a recovered task status
        now = datetime.now()
        recovered_status = LessonGenerationStatus(
            lesson_id=lesson_id,
            status=GenerationStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            topics=topics or ["recovered"],
            progress={"percentage": 100.0, "current_step": "Recovered from filesystem"},
            result_files=result_files,
            download_url=f"/api/v1/lessons/{lesson_id}/download",
            zip_file_path=str(zip_path),
        )    # Add to task manager
    task_manager.tasks[lesson_id] = recovered_status
    
    return {"message": f"Lesson {lesson_id} recovered successfully", "status": recovered_status}


@router.post("/generate", response_model=LessonGenerationResponse)
async def generate_lesson(
    request: LessonGenerationRequest,
    background_tasks: BackgroundTasks,
    task_manager = Depends(get_database_task_manager),
):
    """
    Start lesson generation for the specified topics.
    
    This endpoint queues a lesson generation task and returns immediately
    with a lesson_id that can be used to track progress.
    """
    
    # Generate unique lesson ID
    lesson_id = f"lesson_{uuid.uuid4().hex[:8]}"

    # Validate required fields
    if not request.modules or not isinstance(request.modules, int) or request.modules < 1:
        raise HTTPException(status_code=422, detail="Number of modules must be a positive integer.")
    
    # Handle topics - use provided or generate with AI if empty
    if request.topics and len(request.topics) > 0:
        topics = request.topics
    else:
        # Generate default topics if none provided (AI generation will be handled later)
        print(f"🔧 DEBUG: No topics provided, using default topic for {request.modules} modules")
        topics = ["programming_fundamentals"]  # Single topic, will generate requested number of modules
        print(f"🔧 DEBUG: Using default topic: {topics}")

    # Create generation config from request or use defaults
    if request.config:
        config = request.config
        # If user supplied a config but omitted modules_count, use the top-level modules value
        if not hasattr(config, 'modules_count') or config.modules_count is None:
            config.modules_count = request.modules
    else:
        import os
        # Write topics directly under generated_lessons/<topic_slug>
        # (previously we used a lesson_id wrapper directory)
        output_dir = Path("generated_lessons")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured in environment")
        config = GenerationConfig(
            output_dir=output_dir,
            modules_count=request.modules,
            difficulty=DifficultyLevel(request.difficulty),
            use_ai=True,
            verbose=True,
            openai_api_key=api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            openai_organization=os.getenv("OPENAI_ORGANIZATION"),
            enable_cache=True,
            rate_limit_delay=0.5,
        )

    # If AI is requested but no OpenAI client is available, surface a hard error
    if config.use_ai and not OPENAI_CLIENT_TYPE:
        raise HTTPException(
            status_code=500,
            detail=(
                "OpenAI client library is not installed in the server environment. "
                "Install the 'openai' package (for modern client use 'openai>=1.0.0') "
                "or ensure the legacy 'openai' package is available, then restart the server."
            )
        )

    # Register the task
    await task_manager.create_task(
        lesson_id=lesson_id,
        topics=topics,
        config=config,
        template_ids=request.template_ids,
    )

    # Start background task
    background_tasks.add_task(
        _run_lesson_generation,
        lesson_id,
        topics,
        config,
        request.template_ids,
        task_manager,
    )

    return LessonGenerationResponse(
        lesson_id=lesson_id,
        status=GenerationStatus.PENDING,
        message=f"Lesson generation queued for {len(topics)} topic(s)",
    )


@router.get("/{lesson_id}/status", response_model=LessonGenerationStatus)
async def get_lesson_status(
    lesson_id: str,
    task_manager = Depends(get_database_task_manager),
):
    """Get the current status of a lesson generation task."""
    
    status = await task_manager.get_task_status(lesson_id)
    if not status:
        raise HTTPException(status_code=404, detail="Lesson generation task not found")
    
    return status


@router.get("/{lesson_id}/download")
async def download_lesson(
    lesson_id: str,
    task_manager = Depends(get_database_task_manager),
):
    """Download the generated lesson files as a ZIP archive."""
    
    status = await task_manager.get_task_status(lesson_id)
    if not status:
        raise HTTPException(status_code=404, detail="Lesson generation task not found")
    
    if status.status != GenerationStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Lesson generation is not completed (status: {status.status})"
        )
    
    try:
        # Create ZIP archive from database
        zip_content = await task_manager.create_lesson_archive(lesson_id)
        
        # Return the ZIP content as a streaming response
        from fastapi.responses import Response
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={lesson_id}_lessons.zip"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create archive: {str(e)}")


@router.get("/{lesson_id}/preview")
async def preview_lesson(
    lesson_id: str,
    task_manager = Depends(get_database_task_manager),
):
    """Preview the lesson structure and content before downloading."""
    
    status = await task_manager.get_task_status(lesson_id)
    if not status:
        raise HTTPException(status_code=404, detail="Lesson generation task not found")
    
    if status.status != GenerationStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Lesson generation is not completed (status: {status.status})"
        )
    
    # Get lesson files from database
    from ...database import SessionLocal
    from ...database.repositories import FileRepository, LessonRepository
    
    db = SessionLocal()
    try:
        file_repo = FileRepository(db)
        lesson_repo = LessonRepository(db)
        
        lesson = lesson_repo.get_lesson(lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found in database")
            
        lesson_files = file_repo.get_lesson_files(lesson_id)
        
        # Build lesson structure preview
        preview_data = {
            "lesson_id": lesson_id,
            "topics": lesson.topics,
            "created_at": lesson.created_at,
            "file_structure": [],
            "readme_content": None,
            "total_files": lesson.total_files,
            "total_size": lesson.total_size,
            "modules": []
        }
        
        # Organize files by path structure
        files_by_path = {}
        readme_content = None
        
        for lesson_file in lesson_files:
            file_path = lesson_file.file_path
            file_size = lesson_file.file_size
            
            # Add to file structure
            preview_data["file_structure"].append({
                "path": file_path,
                "type": "file",
                "size": file_size,
                "extension": Path(file_path).suffix[1:] if Path(file_path).suffix else None
            })
            
            # Check if this is a README file
            if Path(file_path).name.lower() in ['readme.md', 'readme.txt']:
                try:
                    content = file_repo.get_file_content(lesson_file.file_id)
                    if content:
                        content_str = content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
                        readme_content = content_str[:2000] + "..." if len(content_str) > 2000 else content_str
                except Exception:
                    readme_content = "Unable to read README content"
        
        preview_data["readme_content"] = readme_content
        
        # Organize files into modules
        module_files = {}
        for lesson_file in lesson_files:
            path_parts = Path(lesson_file.file_path).parts
            # Look for module directories
            for part in path_parts:
                if part.startswith('module_'):
                    if part not in module_files:
                        module_files[part] = []
                    module_files[part].append({
                        "name": Path(lesson_file.file_path).name,
                        "type": Path(lesson_file.file_path).suffix[1:] if Path(lesson_file.file_path).suffix else "unknown",
                        "size": lesson_file.file_size,
                        "path": lesson_file.file_path
                    })
                    break
        
        # Convert to module list
        for module_name in sorted(module_files.keys()):
            preview_data["modules"].append({
                "name": module_name,
                "files": sorted(module_files[module_name], key=lambda f: f["name"])
            })
        
        return preview_data
        
    finally:
        db.close()


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    task_manager = Depends(get_database_task_manager),
):
    """Delete a lesson generation task and clean up associated files."""
    
    success = await task_manager.cleanup_task(lesson_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lesson generation task not found")
    
    return {"message": f"Lesson generation task {lesson_id} deleted successfully"}


@router.post("/recover-all")
async def recover_all_lessons(
    task_manager = Depends(get_database_task_manager),
):
    """Recover all lessons that exist on filesystem but not in memory."""
    
    from datetime import datetime
    import zipfile
    import tempfile
    
    lessons_dir = Path("generated_lessons")
    if not lessons_dir.exists():
        return {"message": "No lessons directory found", "recovered": []}
    
    recovered_lessons = []
    
    for lesson_dir in lessons_dir.iterdir():
        if not lesson_dir.is_dir() or not lesson_dir.name.startswith('lesson_'):
            continue
        
        lesson_id = lesson_dir.name
        
        # Skip if already in memory
        if lesson_id in task_manager.tasks:
            continue
        
        # Collect all files in the lesson directory
        result_files = []
        for file_path in lesson_dir.rglob('*'):
            if file_path.is_file():
                result_files.append(str(file_path))
        
        if not result_files:
            continue
        
        # Create ZIP file for download
        temp_dir = Path(tempfile.gettempdir()) / "lesson_generator" / lesson_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = temp_dir / f"{lesson_id}_lessons.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in result_files:
                rel_path = Path(file_path).relative_to(lesson_dir.parent)
                zipf.write(file_path, rel_path)
        
        # Infer topics from directory structure
        topics = []
        for item in lesson_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                topics.append(item.name)
        
        # Create a recovered task status
        now = datetime.now()
        recovered_status = LessonGenerationStatus(
            lesson_id=lesson_id,
            status=GenerationStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            topics=topics or ["recovered"],
            progress={"percentage": 100.0, "current_step": "Recovered from filesystem"},
            result_files=result_files,
            download_url=f"/api/v1/lessons/{lesson_id}/download",
            zip_file_path=str(zip_path),
        )
        
        # Add to task manager
        task_manager.tasks[lesson_id] = recovered_status
        recovered_lessons.append(lesson_id)
    
    return {"message": f"Recovered {len(recovered_lessons)} lessons", "recovered": recovered_lessons}


@router.get("/", response_model=List[LessonGenerationStatus])
async def list_lessons(
    status: Optional[GenerationStatus] = None,
    limit: int = 50,
    task_manager = Depends(get_database_task_manager),
):
    """List all lesson generation tasks, optionally filtered by status."""
    
    tasks = await task_manager.list_tasks(status=status, limit=limit)
    return tasks


async def _run_lesson_generation(
    lesson_id: str,
    topics: List[str],
    config: GenerationConfig,
    template_ids: Optional[List[str]],
    task_manager,
):
    """
    Background task to run lesson generation.
    
    This function runs the actual lesson generation process and updates
    the task status throughout the process.
    """
    
    try:
        # Ensure modules_count is provided in the generation config
        if not hasattr(config, 'modules_count') or config.modules_count is None:
            raise ValueError(
                "Generation config missing 'modules_count'. Provide 'modules' in the request or include modules_count in the config."
            )
        # Update status to processing
        await task_manager.update_task_status(
            lesson_id, 
            GenerationStatus.PROCESSING,
            message="Initializing lesson generation...",
            progress=2.0,
        )
        
        # Create lesson generator instance
        await task_manager.update_task_status(
            lesson_id, 
            GenerationStatus.PROCESSING,
            message="Setting up lesson generator...",
            progress=5.0,
        )
        generator = LessonGenerator(config)
        
        # Process each topic
        all_results = []
        total_topics = len(topics)
        
        # Each topic gets the same number of modules (modules per lesson)
        # The modules parameter controls the number of modules PER lesson
        modules_per_topic = [config.modules_count] * total_topics
        
        await task_manager.update_task_status(
            lesson_id, 
            GenerationStatus.PROCESSING,
            message=f"Planning lesson structure for {total_topics} topic(s)...",
            progress=8.0,
        )
        
        print(f"🔧 DEBUG: Each lesson will have {config.modules_count} modules ({total_topics} topics = {total_topics} lessons)")
        
        print(f"🔧 DEBUG: Module distribution plan: {modules_per_topic} (modules per lesson: {config.modules_count}, total lessons: {total_topics})")
        
        for i, topic in enumerate(topics):
            # Update progress for topic start
            base_progress = (i / total_topics) * 85  # Reserve 15% for final steps
            await task_manager.update_task_status(
                lesson_id,
                GenerationStatus.PROCESSING,
                message=f"Starting lesson generation for '{topic}' ({i+1}/{total_topics})",
                progress=base_progress,
            )
            
            modules_for_this_topic = modules_per_topic[i]
            print(f"🔧 DEBUG: Topic '{topic}' will get {modules_for_this_topic} modules")
            
            # Convert topic string to TopicConfig object
            print(f"🔧 DEBUG: About to call create_topic_from_name with modules_count={modules_for_this_topic}")
            topic_config = create_topic_from_name(
                topic_name=topic,
                difficulty=config.difficulty.value,
                modules_count=modules_for_this_topic
            )
            print(f"🔧 DEBUG: Topic config created with {len(topic_config.modules)} modules: {[m.name for m in topic_config.modules]}")
            
            # Calculate progress for this topic
            topic_progress_base = (i / total_topics) * 85
            topic_progress_share = 85 / total_topics
            
            # Show detailed preparation
            await task_manager.update_task_status(
                lesson_id,
                GenerationStatus.PROCESSING,
                message=f"📚 Starting lesson '{topic}' with {len(topic_config.modules)} modules...",
                progress=topic_progress_base,
            )
            
            # Generate lesson with detailed progress simulation
            print(f"🔧 DEBUG: Starting generation for topic: {topic}")
            
            # Show detailed steps that users will find engaging
            steps = [
                f"📚 Preparing lesson structure for '{topic}'...",
                f"📝 Generating learning materials and starter code...",
                f"🧪 Creating assignments and test files...",
                f"✨ Finalizing lesson content and examples...",
            ]
            
            for step_i, step_msg in enumerate(steps):
                step_progress = topic_progress_base + (step_i / len(steps)) * topic_progress_share * 0.8
                await task_manager.update_task_status(
                    lesson_id,
                    GenerationStatus.PROCESSING,
                    message=step_msg,
                    progress=step_progress,
                )
                # Small delay to show progression
                import asyncio
                await asyncio.sleep(0.2)
            
            # Start actual generation
            await task_manager.update_task_status(
                lesson_id,
                GenerationStatus.PROCESSING,
                message=f"🚀 Generating lesson files for '{topic}' (this may take a moment)...",
                progress=topic_progress_base + topic_progress_share * 0.9,
            )
            
            # Actually generate the lesson
            result = await generator.generate_lesson_async(topic_config)
            print(f"🔧 DEBUG: Generation result: {result}")
            print(f"🔧 DEBUG: Result type: {type(result)}")
            if result and hasattr(result, 'output_dir'):
                print(f"🔧 DEBUG: Output dir: {result.output_dir}")
            all_results.append(result)
            
            # Update completion for this topic
            await task_manager.update_task_status(
                lesson_id,
                GenerationStatus.PROCESSING,
                message=f"✅ Completed lesson '{topic}' ({i+1}/{total_topics})",
                progress=((i + 1) / total_topics) * 85,
            )
            
            # Update progress after completion
            progress = ((i + 1) / total_topics) * 85
            await task_manager.update_task_status(
                lesson_id,
                GenerationStatus.PROCESSING,
                message=f"Completed lesson for '{topic}' ({i+1}/{total_topics})",
                progress=progress,
            )
        
        # Update progress for file processing
        await task_manager.update_task_status(
            lesson_id,
            GenerationStatus.PROCESSING,
            message="Processing and storing generated files...",
            progress=87.0,
        )
        
        # Store lesson files in database
        print(f"🔧 DEBUG: About to store files. Results count: {len(all_results)}")
        print(f"🔧 DEBUG: Results: {[str(r) for r in all_results]}")
        await task_manager.store_lesson_files(lesson_id, all_results)
        
        # Update progress for file collection
        await task_manager.update_task_status(
            lesson_id,
            GenerationStatus.PROCESSING,
            message="Collecting generated lesson files...",
            progress=93.0,
        )
        
        # Collect all generated file paths
        all_result_files = []
        for result in all_results:
            if result and hasattr(result, 'output_dir') and result.output_dir:
                output_path = Path(result.output_dir)
                if output_path.exists():
                    for file_path in output_path.rglob('*'):
                        if file_path.is_file():
                            all_result_files.append(str(file_path))
        
        # Final progress update
        await task_manager.update_task_status(
            lesson_id,
            GenerationStatus.PROCESSING,
            message="Finalizing lesson generation...",
            progress=98.0,
        )
        
        # Mark as completed
        await task_manager.update_task_status(
            lesson_id,
            GenerationStatus.COMPLETED,
            message=f"Successfully generated {len(topics)} lesson(s) with {len(all_result_files)} files",
            progress=100.0,
            download_url=f"/api/v1/lessons/{lesson_id}/download",
            result_files=all_result_files,
        )
        
    except Exception as e:
        # Handle errors
        error_message = f"Lesson generation failed: {str(e)}"
        await task_manager.update_task_status(
            lesson_id,
            GenerationStatus.FAILED,
            message=error_message,
            error_message=error_message,
        )