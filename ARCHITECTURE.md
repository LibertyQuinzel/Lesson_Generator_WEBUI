# Lesson Generator - System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LESSON GENERATOR SYSTEM                  │
├─────────────────────────────────────────────────────────────┤
│  Interface Layer                                            │
│  ├── CLI Interface (Click)                                  │
│  │   ├── Command Parser                                     │
│  │   ├── Validation Layer                                   │
│  │   └── Progress Reporter                                  │
│  └── Web Interface (FastAPI)                               │
│      ├── REST API (OpenAPI/Swagger)                        │
│      ├── Background Task Queue                             │
│      ├── Static File Serving                               │
│      └── WebSocket/SSE for Real-time Updates               │
├─────────────────────────────────────────────────────────────┤
│  Web Frontend (React + TypeScript)                         │
│  ├── Lesson Generation UI                                  │
│  ├── Progress Tracking Dashboard                           │
│  ├── File Management Interface                             │
│  ├── Configuration Management                              │
│  └── Responsive Mobile Support                             │
├─────────────────────────────────────────────────────────────┤
│  Core Generator Engine                                      │
│  ├── LessonGenerator (Main Orchestrator)                   │
│  ├── TopicProcessor (Topic → Content Mapping)              │
│  ├── TemplateEngine (Jinja2 Templates)                     │
│  └── FileStructureManager (Directory Creation)             │
├─────────────────────────────────────────────────────────────┤
│  Content Generation Layer                                   │
│  ├── OpenAI Content Generator                              │
│  ├── Code Example Generator                                │
│  ├── Assignment Creator                                     │
│  └── Test Case Generator                                    │
├─────────────────────────────────────────────────────────────┤
│  Quality Assurance Layer                                   │
│  ├── Code Validator (AST + Syntax Check)                   │
│  ├── Test Runner (Pytest Integration)                      │
│  ├── Linting Engine (Pylint + Black)                       │
│  └── Content Reviewer                                       │
├─────────────────────────────────────────────────────────────┤
│  Configuration & Templates                                  │
│  ├── Topic Configuration (JSON Schema)                     │
│  ├── Jinja2 Templates                                       │
│  ├── Code Templates                                         │
│  └── Test Templates                                         │
├─────────────────────────────────────────────────────────────┤
│  External Services                                          │
│  ├── OpenAI API (GPT-4 for content)                       │
│  ├── File System I/O                                       │
│  └── Git Integration (Optional)                            │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Component Architecture

### 1. **Interface Layer**

#### **CLI Interface (Click Framework)**
- **Technology**: Click framework
- **Responsibilities**: 
  - Parse command-line arguments
  - Validate input parameters
  - Display progress and results
  - Handle error reporting
- **Key Components**:
  - `CommandParser`: Main CLI entry point
  - `InputValidator`: Validate topics, paths, configurations
  - `ProgressReporter`: Show generation progress

#### **Web Interface (FastAPI)**
- **Technology**: FastAPI + Uvicorn
- **Responsibilities**:
  - REST API endpoints for all CLI functionality
  - Background task processing for long-running operations
  - File serving and download management
  - Real-time progress updates via WebSocket/SSE
  - Request validation and error handling
- **Key Components**:
  - `FastAPIApp`: Main web application
  - `LessonRouter`: Lesson generation endpoints
  - `ConfigRouter`: Configuration management endpoints
  - `FileRouter`: File serving and download endpoints
  - `TaskQueue`: Background task processing
  - `WebSocketManager`: Real-time updates

### 2. **Web Frontend Layer**
- **Technology**: React + TypeScript + Vite
- **Responsibilities**:
  - User interface for lesson generation
  - Real-time progress tracking
  - File management and downloads
  - Configuration management
  - Responsive design for mobile/desktop
- **Key Components**:
  - `LessonGenerationForm`: Topic input and configuration
  - `ProgressDashboard`: Real-time generation tracking
  - `FileManager`: Upload/download interface
  - `ConfigurationPanel`: Settings and templates management
  - `HistoryView`: Past generation results
- **State Management**: React hooks with Context API
- **API Integration**: Axios with TypeScript interfaces
- **Real-time Updates**: WebSocket/EventSource integration

### 3. **Core Generator Engine**
- **Technology**: Pure Python with dependency injection
- **Responsibilities**:
  - Orchestrate the entire lesson generation process
  - Manage dependencies between components
  - Handle configuration and state management
- **Key Components**:
  - `LessonGenerator`: Main orchestrator class
  - `TopicProcessor`: Convert topics to structured data
  - `TemplateEngine`: Jinja2 template processing
  - `FileStructureManager`: Directory and file creation

### 4. **Content Generation Layer**
- **Technology**: OpenAI API + Python AST + Jinja2
- **Responsibilities**:
  - Generate topic-specific content using AI
  - Create code examples and assignments
  - Generate test cases and documentation
- **Key Components**:
  - `OpenAIContentGenerator`: AI-powered content creation
  - `CodeExampleGenerator`: Programming examples
  - `AssignmentCreator`: Student assignments
  - `TestCaseGenerator`: Unit test creation

### 5. **Quality Assurance Layer**
- **Technology**: AST, Pylint, Black, Pytest
- **Responsibilities**:
  - Validate generated code syntax
  - Ensure code quality standards
  - Run generated tests
  - Content consistency checks
- **Key Components**:
  - `CodeValidator`: Syntax and structure validation
  - `TestRunner`: Execute generated tests
  - `LintingEngine`: Code style enforcement
  - `ContentReviewer`: Content quality checks

## 🌐 Web API Architecture

### API Design Principles
- **RESTful Design**: Standard HTTP methods and status codes
- **Async Processing**: Background tasks for long-running operations
- **Real-time Updates**: WebSocket/SSE for progress tracking
- **File Management**: Secure upload/download with cleanup
- **Error Handling**: Consistent error responses with details

### API Endpoints Structure
```
/api/v1/
├── lessons/
│   ├── POST /generate              # Start lesson generation
│   ├── GET /{id}/status           # Check generation progress
│   ├── GET /{id}/download         # Download generated files
│   ├── GET /{id}/preview          # Preview lesson structure
│   └── DELETE /{id}               # Clean up generated files
├── config/
│   ├── POST /validate-topic       # Validate topic configuration
│   ├── GET /templates             # List available templates
│   ├── POST /templates            # Upload custom template
│   └── GET /defaults              # Get default configurations
├── system/
│   ├── GET /health                # System health check
│   ├── GET /status                # Current system status
│   └── GET /metrics               # Usage metrics
└── ws/
    └── /progress/{lesson_id}      # WebSocket for real-time updates
```

### Background Task Processing
- **Task Queue**: FastAPI BackgroundTasks or Celery for scalability
- **Progress Tracking**: Redis/in-memory storage for status updates
- **File Cleanup**: Automated cleanup of temporary and completed files
- **Error Recovery**: Graceful error handling with detailed logging

## 🔄 Data Flow Architecture

### CLI Data Flow
```
CLI Input (Topics + Config) 
    ↓
Topic Processing (Parse & Structure)
    ↓
Content Generation (OpenAI + Templates)
    ↓
Code Generation (Examples + Assignments)
    ↓
Quality Assurance (Validation + Testing)
    ↓
File System Output (Structured Lessons)
    ↓
Post-processing (Documentation + Packaging)
```

### Web Application Data Flow
```
Frontend Form Submission
    ↓
FastAPI Request Validation (Pydantic)
    ↓
Background Task Queuing
    ↓
[Same Core Generation Process as CLI]
    ↓
Real-time Progress Updates (WebSocket)
    ↓
File Storage & Download Links
    ↓
Cleanup & Notification
```

## 🗃️ Data Models

### Topic Configuration Schema
```json
{
  "topic": {
    "name": "string",
    "difficulty": "beginner|intermediate|advanced",
    "concepts": ["list", "of", "concepts"],
    "learning_objectives": ["list", "of", "objectives"],
    "prerequisites": ["list", "of", "prereqs"],
    "estimated_hours": "number",
    "modules": [
      {
        "name": "string",
        "type": "starter|assignment|extra",
        "focus_areas": ["list", "of", "areas"],
        "code_complexity": "simple|moderate|complex"
      }
    ]
  }
}
```

### Lesson Structure Schema
```json
{
  "lesson": {
    "title": "string",
    "description": "string",
    "modules": [
      {
        "name": "string",
        "files": {
          "learning_path": "content",
          "starter_example": "code",
          "assignment_a": "code",
          "assignment_b": "code",
          "test_files": ["list", "of", "test", "files"],
          "extra_exercises": "content"
        }
      }
    ],
    "config_files": ["requirements.txt", "pytest.ini", "Makefile"],
    "metadata": {
      "created_at": "timestamp",
      "generator_version": "string",
      "ai_model_used": "string"
    }
  }
}
```

## 🔌 Integration Points

### OpenAI API Integration
```python
class OpenAIContentGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    async def generate_learning_content(self, topic: Topic) -> LearningContent:
        # Generate structured learning content
        pass
    
    async def generate_code_example(self, concept: str, difficulty: str) -> CodeExample:
        # Generate code examples
        pass
```

### Template Engine Integration
```python
class TemplateEngine:
    def __init__(self, templates_dir: Path):
        self.env = Environment(loader=FileSystemLoader(templates_dir))
    
    def render_learning_path(self, topic: Topic, content: LearningContent) -> str:
        # Render learning path markdown
        pass
    
    def render_assignment(self, assignment_data: AssignmentData) -> str:
        # Render assignment Python files
        pass
```

## 🚀 Scalability & Performance

### Concurrent Processing
- **Async/Await**: Use asyncio for OpenAI API calls
- **Thread Pools**: Parallel file I/O operations
- **Batch Processing**: Generate multiple lessons simultaneously

### Caching Strategy
- **Template Caching**: Cache compiled Jinja2 templates
- **API Response Caching**: Cache similar OpenAI responses
- **Configuration Caching**: Cache parsed topic configurations

### Resource Management
- **Rate Limiting**: Respect OpenAI API rate limits
- **Memory Management**: Stream large file operations
- **Error Resilience**: Retry mechanisms with exponential backoff

## 🛡️ Error Handling & Logging

### Error Categories
1. **Input Validation Errors**: Invalid topics, missing configurations
2. **API Errors**: OpenAI API failures, rate limiting
3. **File System Errors**: Permission issues, disk space
4. **Code Generation Errors**: Invalid syntax, template failures
5. **Quality Assurance Errors**: Test failures, lint issues

### Logging Strategy
```python
import structlog

logger = structlog.get_logger()

# Structured logging throughout the application
logger.info("lesson_generation_started", 
           topic=topic_name, 
           modules=module_count,
           timestamp=datetime.now())
```

## 🔒 Security Considerations

### API Key Management
- Environment variables for OpenAI API keys
- Key validation before processing
- Secure key storage recommendations

### Code Safety
- AST-based code validation before execution
- Sandboxed test execution
- Input sanitization for all user-provided data

### File System Security
- Path traversal prevention
- Permission checks before file operations
- Temporary directory cleanup

---

## 📁 Enhanced Project Structure

```
lesson_generator/
├── src/
│   ├── lesson_generator/
│   │   ├── __init__.py
│   │   ├── cli.py                  # Existing CLI interface
│   │   ├── core.py                 # Main generator engine
│   │   ├── content.py              # Content generation
│   │   ├── models.py               # Pydantic models
│   │   ├── quality.py              # Quality assurance
│   │   ├── templates.py            # Template engine
│   │   ├── web/                    # NEW: Web interface
│   │   │   ├── __init__.py
│   │   │   ├── main.py             # FastAPI application
│   │   │   ├── dependencies/       # FastAPI dependencies
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py         # Authentication (future)
│   │   │   │   └── tasks.py        # Background task management
│   │   │   ├── routers/           # API route definitions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── lessons.py      # Lesson generation endpoints
│   │   │   │   ├── config.py       # Configuration endpoints
│   │   │   │   ├── files.py        # File management endpoints
│   │   │   │   └── system.py       # System status endpoints
│   │   │   ├── models/            # Web-specific Pydantic models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── requests.py     # API request models
│   │   │   │   ├── responses.py    # API response models
│   │   │   │   └── websocket.py    # WebSocket message models
│   │   │   ├── services/          # Web application services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── task_manager.py # Background task service
│   │   │   │   ├── file_manager.py # File upload/download service
│   │   │   │   └── websocket.py    # WebSocket connection manager
│   │   │   └── static/            # Static web assets
│   │   │       ├── css/
│   │   │       ├── js/
│   │   │       └── index.html      # Basic web interface
│   │   ├── templates/             # Jinja2 templates
│   │   │   ├── learning_path.md.j2
│   │   │   ├── assignment.py.j2
│   │   │   ├── starter_example.py.j2
│   │   │   └── test_template.py.j2
│   │   └── utils/                 # Utility modules
│   │       ├── __init__.py
│   │       └── validation.py
├── frontend/                      # NEW: React frontend (optional)
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── forms/            # Form components
│   │   │   ├── layout/           # Layout components
│   │   │   └── common/           # Reusable components
│   │   ├── pages/                # Route components
│   │   │   ├── Generate.tsx      # Lesson generation page
│   │   │   ├── History.tsx       # Generation history
│   │   │   └── Settings.tsx      # Configuration page
│   │   ├── hooks/                # Custom React hooks
│   │   ├── services/             # API services
│   │   │   └── api.ts            # Backend API client
│   │   └── utils/                # Frontend utilities
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── tests/
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   ├── e2e/                      # End-to-end tests
│   └── web/                      # NEW: Web-specific tests
│       ├── test_api.py           # API endpoint tests
│       ├── test_websocket.py     # WebSocket tests
│       └── test_background_tasks.py # Background task tests
├── config/
│   ├── topic_schemas/
│   ├── default_topics.json
│   └── web/                      # NEW: Web configuration
│       ├── cors.json            # CORS settings
│       └── rate_limits.json     # Rate limiting config
├── docker/                      # NEW: Docker configuration
│   ├── Dockerfile              # Multi-stage Docker build
│   ├── docker-compose.yml      # Development environment
│   └── docker-compose.prod.yml # Production environment
├── deployment/                  # NEW: Deployment configurations
│   ├── nginx/                   # Nginx configuration
│   ├── systemd/                 # Systemd service files
│   └── kubernetes/              # K8s manifests (optional)
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
├── README.md                   # Project documentation
├── WEB_INTERFACE_SPRINT_PLAN.md # NEW: Web development plan
└── docker-compose.yml          # NEW: Development setup
```