"""
System status and health check API endpoints.

This module provides endpoints for system monitoring, health checks,
and usage metrics.
"""

import time
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from ..models import SystemHealth


router = APIRouter()

# Application start time (set in main.py)
_start_time = None


def set_start_time(start_time: float):
    """Set the application start time."""
    global _start_time
    _start_time = start_time


@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """
    Get comprehensive system health information.
    """
    
    uptime = time.time() - (_start_time or time.time())
    
    # Check OpenAI API availability
    openai_available = True
    try:
        import openai
        # TODO: Add actual API connectivity test
        # openai.api_key = os.getenv("OPENAI_API_KEY")
        # Simple check - if key is set
        openai_available = bool(os.getenv("OPENAI_API_KEY"))
    except ImportError:
        openai_available = False
    
    # Check storage availability
    storage_available = True
    try:
        temp_dir = Path("/tmp")
        test_file = temp_dir / "health_check.tmp"
        test_file.write_text("test")
        test_file.unlink()
    except Exception:
        storage_available = False
    
    # TODO: Get actual count of active generation tasks
    active_generations = 0
    
    return SystemHealth(
        status="healthy" if (openai_available and storage_available) else "degraded",
        version="1.0.0",
        uptime=uptime,
        openai_api_available=openai_available,
        storage_available=storage_available,
        active_generations=active_generations,
    )


@router.get("/status")
async def get_system_status():
    """
    Get basic system status information.
    """
    
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - (_start_time or time.time()),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "working_directory": str(Path.cwd()),
    }


@router.get("/metrics")
async def get_system_metrics():
    """
    Get system usage metrics and statistics.
    """
    
    # TODO: Implement proper metrics collection
    # - Number of lessons generated
    # - API request counts
    # - Error rates
    # - Performance metrics
    
    return {
        "lessons_generated_today": 0,
        "total_lessons_generated": 0,
        "api_requests_today": 0,
        "average_generation_time": 0.0,
        "error_rate": 0.0,
        "active_users": 1,
        "storage_usage_bytes": 0,
    }