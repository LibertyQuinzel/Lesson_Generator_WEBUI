"""
FastAPI web interface for the Lesson Generator.

This module provides a REST API and web interface for generating programming lessons.
It wraps the existing CLI functionality with a modern web API, including background
task processing and real-time progress updates.
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parents[3] / '.env'
    load_dotenv(env_path)
    print(f"🔧 Loading environment from: {env_path}")
    if env_path.exists():
        print(f"✅ .env file found and loaded")
        # Verify API key is loaded
        api_key = os.getenv('OPENAI_API_KEY', '')
        if api_key:
            print(f"🔑 OPENAI_API_KEY loaded (length: {len(api_key)})")
        else:
            print("⚠️  OPENAI_API_KEY not found in environment")
    else:
        print(f"❌ .env file not found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, that's ok")

from .routers import lessons, config, files, system
from .services.task_manager import TaskManager
from .services.database_task_manager import DatabaseTaskManager
from .services.websocket import WebSocketManager
from ..database import async_init_database, async_check_database_health


# Global state for the application
app_state = {
    "start_time": None,
    "task_manager": None,
    "websocket_manager": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    app_state["start_time"] = time.time()
    
    # Initialize database
    print("🗄️ Initializing database...")
    try:
        await async_init_database()
        db_healthy = await async_check_database_health()
        if db_healthy:
            print("✅ Database initialization successful")
        else:
            print("⚠️ Database health check failed")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    
    # Use database-powered task manager
    app_state["task_manager"] = DatabaseTaskManager()
    app_state["websocket_manager"] = WebSocketManager()
    
    print("🚀 Lesson Generator Web Interface starting up...")
    print(f"📁 Working directory: {os.getcwd()}")
    print("🗄️ Using database storage for lessons")
    
    yield
    
    # Shutdown
    if app_state["task_manager"]:
        await app_state["task_manager"].cleanup()
    print("🛑 Lesson Generator Web Interface shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Lesson Generator API",
        description="AI-powered lesson generator for programming courses",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["lessons"])
    app.include_router(config.router, prefix="/api/v1/config", tags=["config"]) 
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
    
    # Serve static files (for the web interface)
    static_dir = Path(__file__).parent / "static-new"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        """Serve the main web interface."""
        static_file = static_dir / "index.html"
        if static_file.exists():
            return static_file.read_text()
        
        # Fallback simple HTML interface
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Lesson Generator</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                .header { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .card { border: 1px solid #dee2e6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
                .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
                .btn:hover { background: #0056b3; }
                .api-link { color: #007bff; text-decoration: none; }
                .api-link:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎓 Lesson Generator Web Interface</h1>
                <p>AI-powered lesson generator for programming courses</p>
            </div>
            
            <div class="card">
                <h2>📖 API Documentation</h2>
                <p>Access the interactive API documentation:</p>
                <ul>
                    <li><a href="/api/docs" class="api-link">Swagger UI Documentation</a></li>
                    <li><a href="/api/redoc" class="api-link">ReDoc Documentation</a></li>
                    <li><a href="/api/openapi.json" class="api-link">OpenAPI JSON Schema</a></li>
                </ul>
            </div>
            
            <div class="card">
                <h2>🚀 Quick Start</h2>
                <p>Generate lessons using the API:</p>
                <pre><code>curl -X POST "http://localhost:8000/api/v1/lessons/generate" \\
     -H "Content-Type: application/json" \\
     -d '{
         "topics": ["python_fundamentals"],
         "difficulty": "intermediate"
     }'</code></pre>
            </div>
            
            <div class="card">
                <h2>📊 System Status</h2>
                <p>Check system health: <a href="/api/v1/system/health" class="api-link">/api/v1/system/health</a></p>
            </div>
        </body>
        </html>
        """
    
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "service": "lesson-generator-web"}
    
    return app


# Create the FastAPI application instance
app = create_app()


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
    log_level: str = "info"
):
    """Run the FastAPI server with Uvicorn."""
    
    print(f"🌐 Starting Lesson Generator Web Interface...")
    print(f"📡 Server will be available at: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/api/docs")
    
    uvicorn.run(
        "lesson_generator.web.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True,
    )


if __name__ == "__main__":
    # Allow running directly with python -m lesson_generator.web.main
    import argparse
    
    parser = argparse.ArgumentParser(description="Lesson Generator Web Interface")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to") 
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    run_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        log_level=args.log_level,
    )