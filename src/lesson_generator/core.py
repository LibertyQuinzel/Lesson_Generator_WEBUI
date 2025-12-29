"""
Core lesson generator implementation.

This module contains the main LessonGenerator class that orchestrates
the entire lesson generation process, including AI content generation,
template rendering, and file structure creation.
"""

import ast
import time
from pathlib import Path
from typing import Optional

from .models import (
    TopicConfig, 
    GenerationConfig, 
    LessonGenerationResult,
    ModuleGenerationResult
)
from .content import ContentGenerator
from .templates import TemplateEngine
from .quality import QualityAssurance
from .utils.validation import validate_topic


class LessonGenerator:
    """
    Main orchestrator for lesson generation.
    
    This class coordinates all aspects of lesson generation including:
    - Content generation using AI or fallback methods
    - Template rendering with Jinja2
    - File structure creation
    - Quality assurance and validation
    """
    
    def __init__(self, config: GenerationConfig):
        """
        Initialize the lesson generator.
        
        Args:
            config: Generation configuration
        """
        self.config = config
        
        # Initialize sub-components
        self.content_generator = ContentGenerator(config)
        self.template_engine = TemplateEngine(config)
        self.quality_assurance = QualityAssurance(config)
        
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.config.verbose:
            print(f"Initialized lesson generator with output: {self.config.output_dir}")
    
    def _validate_python_syntax(self, content: str, filename: str = "file") -> tuple[bool, str]:
        """
        Validate Python code for syntax errors.
        
        Args:
            content: Python code content to validate
            filename: Filename for error reporting
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            ast.parse(content)
            return True, ""
        except SyntaxError as e:
            error_msg = f"Syntax error in {filename} at line {e.lineno}: {e.msg}"
            if self.config.verbose:
                print(f"⚠ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Parse error in {filename}: {str(e)}"
            if self.config.verbose:
                print(f"⚠ {error_msg}")
            return False, error_msg
    
    def _fix_common_syntax_issues(self, content: str, filename: str) -> str:
        """
        Try to fix common syntax issues in generated Python code.
        
        Args:
            content: Python code with potential syntax issues
            filename: Filename for logging
            
        Returns:
            Fixed Python code
        """
        if self.config.verbose:
            print(f"Attempting to fix syntax issues in {filename}")
        
        # Common fixes
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix invalid class names (remove hyphens)
            if line.strip().startswith('class ') and '-' in line:
                line = line.replace('-', '')
                if self.config.verbose:
                    print(f"Fixed class name on line {i+1}")
            
            # Fix unclosed docstrings
            if '"""' in line and line.count('"""') == 1:
                # Check if this starts a docstring that never closes
                remaining_lines = lines[i+1:]
                has_closing = any('"""' in l for l in remaining_lines)
                if not has_closing:
                    # Add closing docstring
                    line += '\n"""'
                    if self.config.verbose:
                        print(f"Added missing closing docstring on line {i+1}")
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def generate_lesson(self, topic: TopicConfig) -> LessonGenerationResult:
        """
        Generate a complete lesson from a topic configuration.
        
        Args:
            topic: Topic configuration
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Generation result with success/failure status and details
        """
        start_time = time.time()
        
        try:
            # Validate topic configuration
            validation_result = validate_topic(topic)
            if not validation_result.is_valid:
                return LessonGenerationResult(
                    topic_name=topic.name,
                    topic_slug=topic.slug,
                    success=False,
                    output_path=self.config.output_dir,
                    error=f"Topic validation failed: {'; '.join(validation_result.errors)}"
                )
            
            if self.config.verbose and validation_result.warnings:
                print(f"Warnings for topic '{topic.name}': {'; '.join(validation_result.warnings)}")
            
            # Check if we need to extract templates from reference lesson
            if (self.config.reference_lesson_dir and 
                Path(self.config.reference_lesson_dir).exists() and 
                not self.template_engine.has_custom_templates()):
                
                if self.config.verbose:
                    print(f"Extracting templates from reference lesson: {self.config.reference_lesson_dir}")
                
                try:
                    self.template_engine.extract_templates_from_reference(self.config.reference_lesson_dir)
                    if self.config.verbose:
                        print("✓ Template extraction completed")
                except Exception as e:
                    if self.config.verbose:
                        print(f"⚠ Template extraction failed: {e}, using built-in templates")
            
            # Create lesson directory
            lesson_dir = self.config.output_dir / topic.slug
            lesson_dir.mkdir(parents=True, exist_ok=True)
            
            if self.config.verbose:
                print(f"Creating lesson in: {lesson_dir}")
                template_source = self.template_engine.get_template_source()
                print(f"Using templates: {template_source}")
            
            # Generate lesson structure
            result = LessonGenerationResult(
                topic_name=topic.name,
                topic_slug=topic.slug,
                success=True,
                output_path=lesson_dir,
                ai_model_used=self.config.openai_model if self.config.use_ai else None
            )
            
            # Generate each module
            for i, module in enumerate(topic.modules):
                if self.config.verbose:
                    print(f"  Generating module: {module.name}")
                
                module_result = self._generate_module(topic, module, lesson_dir)
                result.modules.append(module_result)
                
                if not module_result.success:
                    result.success = False
                    if not result.error:
                        result.error = f"Failed to generate module: {module.name}"
            
            # Generate lesson-level configuration files
            if result.success:
                self._generate_lesson_config_files(topic, lesson_dir, result)
            
            # Run quality assurance if lesson generation was successful
            if result.success:
                if self.config.verbose:
                    print("  Running quality assurance...")
                
                quality_report = self.quality_assurance.validate_lesson(lesson_dir)
                result.quality_report = quality_report
                
                # Mark as failed if quality is too low
                if quality_report.quality_score < 0.5:
                    result.success = False
                    result.error = f"Quality score too low: {quality_report.quality_score:.2f}"
            
            # Calculate generation time
            result.generation_time_seconds = time.time() - start_time
            
            if self.config.verbose:
                status = "✓" if result.success else "✗"
                print(f"  {status} Lesson generation completed in {result.generation_time_seconds:.2f}s")
                
                # Print cost optimization summary
                self.content_generator.print_cost_summary()
            
            return result
            
        except Exception as e:
            return LessonGenerationResult(
                topic_name=topic.name,
                topic_slug=topic.slug,
                success=False,
                output_path=self.config.output_dir,
                error=f"Unexpected error: {str(e)}",
                generation_time_seconds=time.time() - start_time
            )
    
    def _generate_module(
        self, 
        topic: TopicConfig, 
        module_config,
        lesson_dir: Path
    ) -> ModuleGenerationResult:
        """
        Generate a single module within a lesson.
        
        Args:
            topic: Topic configuration
            module_config: Module configuration
            lesson_dir: Lesson directory path
            
        Returns:
            Module generation result
        """
        start_time = time.time()
        
        try:
            # Create module directory
            module_name = module_config.name.lower().replace(' ', '_')
            module_dir = lesson_dir / f"module_{module_name}"
            module_dir.mkdir(parents=True, exist_ok=True)
            
            result = ModuleGenerationResult(
                module_name=module_config.name,
                success=True
            )
            
            # Generate module files based on type
            if module_config.type in ["starter", "assignment", "project"]:
                # Standard module files
                self._generate_standard_module_files(topic, module_config, module_dir, result)
            elif module_config.type == "extra":
                # Extra exercises only
                self._generate_extra_module_files(topic, module_config, module_dir, result)
            
            result.generation_time_seconds = time.time() - start_time
            return result
            
        except Exception as e:
            return ModuleGenerationResult(
                module_name=module_config.name,
                success=False,
                error=str(e),
                generation_time_seconds=time.time() - start_time
            )
    
    def _generate_standard_module_files(self, topic, module_config, module_dir, result):
        """Generate standard files for a module."""
        
        # Define file types and their corresponding content types
        files_to_generate = {
            "learning_path.md": ("learning_path", "learning_path.md.j2"),
            "starter_example.py": ("starter_example", "assignment.py.j2"),
            "test_starter_example.py": ("test_starter", "test_template.py.j2"),
            "assignment_a.py": ("assignment_a", "assignment.py.j2"),
            "test_assignment_a.py": ("test_assignment_a", "test_template.py.j2"),
            "assignment_b.py": ("assignment_b", "assignment.py.j2"),
            "test_assignment_b.py": ("test_assignment_b", "test_template.py.j2"),
            "extra_exercises.md": ("extra_exercises", "extra_exercises.md.j2")
        }
        
        # Store generated content for contextual generation
        generated_content = {}
        
        for filename, (content_type, template_name) in files_to_generate.items():
            try:
                # For test files, include the corresponding code file content as context
                extra_context = {}
                if filename.startswith('test_'):
                    # Get the corresponding code file
                    code_file = filename.replace('test_', '', 1)
                    if code_file in generated_content:
                        extra_context['code_to_test'] = generated_content[code_file]
                        if self.config.verbose:
                            print(f"    Adding code context for {filename}: {code_file} ({len(generated_content[code_file])} chars)")
                    else:
                        if self.config.verbose:
                            print(f"    No code context available for {filename} (looking for {code_file})")
                            print(f"    Available files: {list(generated_content.keys())}")
                
                # Generate content using AI or fallback
                content_response = self.content_generator.generate_content(
                    content_type, topic, module_config, extra_context
                )
                
                # Prepare template context
                context = self._create_template_context(topic, module_config, content_type, content_response, extra_context)
                
                # Determine content source based on type and AI availability
                if filename.endswith('.md') and content_response.model_used != "fallback":
                    # Always use AI for markdown files when available
                    if self.config.verbose:
                        print(f"    Using AI-generated content for {filename}")
                    content = content_response.content
                elif filename.startswith(('assignment_', 'starter_')) and content_response.model_used != "fallback":
                    # Use AI for assignment and starter files when available
                    if self.config.verbose:
                        print(f"    Using AI-generated content for {filename}")
                    content = content_response.content
                elif filename.startswith('test_') and extra_context.get('code_to_test') and content_response.model_used != "fallback":
                    # Use AI for test files with contextual information
                    if self.config.verbose:
                        print(f"    Using AI-generated content for {filename} (contextual test generation)")
                    content = content_response.content
                elif self.template_engine.template_exists(template_name):
                    # Use template as fallback
                    if self.config.verbose:
                        print(f"    Using template: {template_name}")
                    content = self.template_engine.render_template(template_name, context)
                else:
                    if self.config.verbose:
                        print(f"    Template {template_name} not found, using generated content")
                    content = content_response.content
                
                # Validate Python syntax before writing
                file_path = module_dir / filename
                if filename.endswith('.py'):
                    is_valid, error_msg = self._validate_python_syntax(content, filename)
                    if not is_valid:
                        # Try to fix common issues
                        content = self._fix_common_syntax_issues(content, filename)
                        # Validate again after fix
                        is_valid, error_msg = self._validate_python_syntax(content, filename)
                        if not is_valid and self.config.verbose:
                            print(f"⚠ Still has syntax errors after fix attempt: {error_msg}")
                
                # Store generated content for contextual generation of related files
                generated_content[filename] = content
                
                file_path.write_text(content, encoding='utf-8')
                
                from .models import GeneratedFile
                generated_file = GeneratedFile(
                    path=file_path,
                    content=content,
                    file_type="python" if filename.endswith('.py') else "markdown",
                    size_bytes=len(content.encode('utf-8'))
                )
                result.files.append(generated_file)
                
                if self.config.verbose:
                    print(f"    ✓ Generated {filename} ({len(content)} chars)")
                
            except Exception as e:
                if self.config.verbose:
                    print(f"    ✗ Failed to generate {filename}: {e}")
                
                # Create minimal fallback file
                fallback_content = f"# {filename}\n\n# Error generating content: {e}\n# TODO: Implement {filename} for {module_config.name}\n"
                file_path = module_dir / filename
                
                # Validate fallback content too if it's Python
                if filename.endswith('.py'):
                    is_valid, error_msg = self._validate_python_syntax(fallback_content, filename)
                    if not is_valid:
                        fallback_content = f'"""\n{filename}\n\nError generating content: {e}\nTODO: Implement {filename} for {module_config.name}\n"""\n\npass\n'
                
                file_path.write_text(fallback_content, encoding='utf-8')
                
                from .models import GeneratedFile
                generated_file = GeneratedFile(
                    path=file_path,
                    content=fallback_content,
                    file_type="python" if filename.endswith('.py') else "markdown",
                    size_bytes=len(fallback_content.encode('utf-8'))
                )
                result.files.append(generated_file)
    
    def _generate_extra_module_files(self, topic, module_config, module_dir, result):
        """Generate files for extra exercises module."""
        file_path = module_dir / "extra_exercises.md"
        content = f"# Extra Exercises: {module_config.name}\n\n# TODO: Implement extra exercises\n"
        
        file_path.write_text(content, encoding='utf-8')
        
        from .models import GeneratedFile
        generated_file = GeneratedFile(
            path=file_path,
            content=content,
            file_type="markdown",
            size_bytes=len(content.encode('utf-8'))
        )
        result.files.append(generated_file)
    
    def _generate_lesson_config_files(self, topic, lesson_dir, result):
        """Generate lesson-level configuration files."""
        config_files = {
            "README.md": self._generate_lesson_readme(topic),
            "requirements.txt": self._generate_requirements_txt(topic),
            "pytest.ini": self._generate_pytest_ini(topic),
            "Makefile": self._generate_makefile(topic),
            "setup.cfg": self._generate_setup_cfg(topic),
            ".gitignore": self._generate_gitignore(topic)
        }
        
        for filename, content in config_files.items():
            file_path = lesson_dir / filename
            file_path.write_text(content, encoding='utf-8')
            
            from .models import GeneratedFile
            generated_file = GeneratedFile(
                path=file_path,
                content=content,
                file_type="text",
                size_bytes=len(content.encode('utf-8'))
            )
            result.config_files.append(generated_file)
    
    def _generate_lesson_readme(self, topic) -> str:
        """Generate main README.md for the lesson."""
        return f"""# {topic.name}

{topic.description}

## Learning Objectives

{chr(10).join(f"- {obj}" for obj in topic.learning_objectives)}

## Prerequisites

{chr(10).join(f"- {prereq}" for prereq in topic.prerequisites) if topic.prerequisites else "None"}

## Modules

{chr(10).join(f"{i+1}. {module.name}" for i, module in enumerate(topic.modules))}

## Getting Started

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\\Scripts\\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run tests: `pytest`

## Estimated Time

This lesson should take approximately {topic.estimated_hours} hours to complete.
"""
    
    def _generate_requirements_txt(self, topic) -> str:
        """Generate requirements.txt for the lesson."""
        return """pytest>=7.0.0
pytest-cov>=4.0.0
pylint>=2.17.0
black>=23.0.0
"""
    
    def _generate_pytest_ini(self, topic) -> str:
        """Generate pytest.ini configuration."""
        return """[tool:pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --tb=short --cov=. --cov-report=term-missing
"""
    
    def _generate_makefile(self, topic) -> str:
        """Generate Makefile for the lesson."""
        return """# Makefile for lesson

.PHONY: test lint format clean install

install:
	pip install -r requirements.txt

test:
	pytest

lint:
	pylint **/*.py

format:
	black **/*.py

clean:
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
"""
    
    def _generate_setup_cfg(self, topic) -> str:
        """Generate setup.cfg configuration."""
        return """[pylint]
disable = missing-docstring,too-few-public-methods

[coverage:run]
source = .
omit = test_*, *_test.py

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
"""
    
    def _generate_gitignore(self, topic) -> str:
        """Generate .gitignore file."""
        return """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    def _create_template_context(self, topic, module_config, content_type, content_response, extra_context=None):
        """Create template context for rendering."""
        # Create a more comprehensive context with fallbacks
        context = {
            'topic': {
                'name': topic.name,
                'slug': topic.slug,
                'description': topic.description,
                'learning_objectives': topic.learning_objectives,
                'prerequisites': topic.prerequisites,
                'estimated_hours': topic.estimated_hours,
                'difficulty': topic.difficulty
            },
            'module': {
                'name': module_config.name,
                'type': module_config.type,
                'description': getattr(module_config, 'description', f'{module_config.name} module description'),
                'learning_objectives': getattr(module_config, 'learning_objectives', [f'Understand {topic.name.lower()} concepts']),
                'estimated_minutes': getattr(module_config, 'estimated_minutes', 60)
            },
            'content_type': content_type,
            'content': content_response.content if content_response else '',
            'metadata': content_response.metadata if content_response else {},
            'generated_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'generator_version': "1.0.0"
        }
        
        # Add content-type specific context
        if content_type in ['assignment_a', 'assignment_b', 'starter_example']:
            # Create valid Python class name by removing hyphens, spaces, and other invalid characters
            safe_topic_name = ''.join(c.title() if c.isalnum() else '' for c in topic.name)
            # Ensure it doesn't start with a number
            if safe_topic_name and safe_topic_name[0].isdigit():
                safe_topic_name = 'Lesson' + safe_topic_name
            if not safe_topic_name or not safe_topic_name.isidentifier():
                safe_topic_name = 'Assignment'
                
            # Create proper descriptions based on assignment type
            if content_type == 'assignment_a':
                description = f'Assignment A: {module_config.name}\nStudents need to write tests to achieve 100% coverage.'
                class_description = 'Assignment class for testing practice.\n\nTASK: Write comprehensive tests for this class in test_assignment_a.py'
            elif content_type == 'assignment_b':
                description = f'Assignment B: {module_config.name}\nStudents need to implement methods to make tests pass.'
                class_description = 'Assignment class for implementation practice.\n\nTASK: Implement the methods below to make the tests in test_assignment_b.py pass.\nFollow the method signatures and docstrings carefully.'
            elif content_type == 'starter_example':
                description = f'Starter Example: {module_config.name}\n\nThis example demonstrates {", ".join(getattr(module_config, "focus_areas", [topic.name.lower()]))} concepts\nin {topic.name.lower()}.'
                class_description = f'Example class for {module_config.name}.\n\nThis class demonstrates key concepts and patterns for this module.\nStudy the implementation to understand best practices.'
            else:
                description = f'{content_type.replace("_", " ").title()}: {module_config.name}'
                class_description = f'Assignment class for {topic.name.lower()} practice.'
                
            context.update({
                'assignment_type': content_type,
                'description': description,
                'learning_objectives': context['module']['learning_objectives'],
                'class_name': f"{safe_topic_name}Assignment",
                'class_description': class_description,
                # Add default methods array to prevent template errors
                'methods': context.get('methods', [
                    {
                        'name': 'process_data',
                        'params': ', data',
                        'description': 'Process input data and return result.',
                        'implementation': 'if not data:\n            return None\n        return str(data).upper()',
                        'param_descriptions': [{'name': 'data', 'description': 'Input data to process'}],
                        'return_description': 'Processed data as uppercase string or None'
                    },
                    {
                        'name': 'validate_input', 
                        'params': ', value',
                        'description': 'Validate input and return boolean.',
                        'implementation': 'return value is not None and len(str(value)) > 0',
                        'param_descriptions': [{'name': 'value', 'description': 'Value to validate'}],
                        'return_description': 'True if valid, False otherwise'
                    }
                ]),
                # Add other required template variables
                'init_code': 'self.data = []',
                'usage_example': f'example = {safe_topic_name}Assignment()\n    result = example.process_data("test")\n    print(result)',
            })
        
        # Add test-specific context - need to define safe_topic_name here too
        if content_type.startswith('test_'):
            # Create valid Python class name - same logic as above
            safe_topic_name = ''.join(c.title() if c.isalnum() else '' for c in topic.name)
            if safe_topic_name and safe_topic_name[0].isdigit():
                safe_topic_name = 'Lesson' + safe_topic_name
            if not safe_topic_name or not safe_topic_name.isidentifier():
                safe_topic_name = 'Assignment'
                
            test_type = content_type.replace('test_', '')
            class_name = f"{safe_topic_name}Assignment" if test_type != 'starter' else f"{safe_topic_name}Example"
            instance_name = class_name.lower().replace('assignment', '_assignment').replace('example', '_example')
            context.update({
                'test_type': test_type,
                'filename': f"test_{test_type}.py" if test_type != 'starter' else "test_starter_example.py",
                'imports': [],
                'class_name': class_name,
                'instance_name': instance_name,
                'test_methods': [],  # Will be filled if needed
                'error_test_methods': [],
                'parametrized_tests': []
            })
        
        # Add extra context if provided (for test files)
        if extra_context and 'code_to_test' in extra_context:
            code_analysis = self._analyze_code_for_testing(extra_context['code_to_test'], content_type)
            context.update(code_analysis)
        elif extra_context:
            context.update(extra_context)
        
        return context
    
    def _analyze_code_for_testing(self, code_content: str, content_type: str) -> dict:
        """Analyze Python code to extract information for test generation."""
        import ast
        import re
        
        analysis = {
            'class_name': None,
            'instance_name': None,
            'test_methods': [],
            'imports': [],
            'test_type': content_type.replace('test_', '') if content_type.startswith('test_') else content_type
        }
        
        try:
            # Parse the Python code
            tree = ast.parse(code_content)
            
            # Find classes and their methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    analysis['class_name'] = class_name
                    analysis['instance_name'] = class_name.lower().replace('example', '').replace('assignment', '') or 'instance'
                    
                    # Extract methods from the class
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                            method_info = {
                                'name': f'test_{item.name}',
                                'description': f'Test {item.name} method functionality.',
                                'setup': f'{analysis["instance_name"]} = {class_name}()',
                                'action': f'result = {analysis["instance_name"]}.{item.name}()',
                                'assertions': 'assert result is not None'
                            }
                            methods.append(method_info)
                    
                    analysis['test_methods'] = methods
                    break  # Use the first class found
            
            # If no class found, create a generic test structure
            if not analysis['class_name']:
                # Try to extract class name from code using regex as fallback
                class_match = re.search(r'class\s+(\w+)', code_content)
                if class_match:
                    analysis['class_name'] = class_match.group(1)
                    analysis['instance_name'] = analysis['class_name'].lower()
                else:
                    # Use a generic name based on content type
                    if 'starter' in content_type:
                        analysis['class_name'] = 'StarterExample'
                    elif 'assignment_a' in content_type:
                        analysis['class_name'] = 'AssignmentA' 
                    elif 'assignment_b' in content_type:
                        analysis['class_name'] = 'AssignmentB'
                    else:
                        analysis['class_name'] = 'TestClass'
                    analysis['instance_name'] = analysis['class_name'].lower()
        
        except Exception as e:
            # If parsing fails, provide sensible defaults
            if self.config.verbose:
                print(f"⚠️ Code analysis failed: {e}")
            
            if 'starter' in content_type:
                analysis['class_name'] = 'StarterExample'
            elif 'assignment_a' in content_type:
                analysis['class_name'] = 'AssignmentA'
            elif 'assignment_b' in content_type:
                analysis['class_name'] = 'AssignmentB'
            else:
                analysis['class_name'] = 'TestClass'
            analysis['instance_name'] = analysis['class_name'].lower()
        
        return analysis
    
    async def generate_lesson_async(self, topic) -> LessonGenerationResult:
        """
        Async wrapper for lesson generation.
        
        This method provides async compatibility for the web interface
        while maintaining the existing synchronous implementation.
        
        Args:
            topic: TopicConfig object or topic name/slug
            
        Returns:
            LessonGenerationResult with generation details
        """
        import asyncio
        
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_lesson, topic)