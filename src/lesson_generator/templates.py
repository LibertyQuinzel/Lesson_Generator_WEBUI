"""
Template engine module.

This module handles Jinja2 template rendering for generating lesson files
with consistent structure and customizable content.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape, Template, TemplateNotFound

from .models import GenerationConfig
from .template_extraction import TemplateExtractor
from .template_extraction import extract_templates_from_reference


class TemplateEngine:
    """
    Handles template rendering using Jinja2.
    
    This class manages the rendering of templates for:
    - Lesson structure files (README, configuration)
    - Module content (learning paths, assignments, tests)
    - Code examples and documentation
    
    Template Priority System:
    1. Custom templates (--templates DIR)
    2. Extracted templates (--reference DIR)  
    3. Built-in templates (default)
    """
    
    def __init__(self, config: GenerationConfig):
        """
        Initialize the template engine.
        
        Args:
            config: Generation configuration
        """
        self.config = config
        self.built_in_templates_dir = Path(__file__).parent / "templates"
        self.template_dirs = []
        self.extracted_templates = {}
        
        # Set up template directory priority
        self._setup_template_directories()
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dirs),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['snake_case'] = self._snake_case_filter
        self.env.filters['title_case'] = self._title_case_filter
        
        if config.verbose:
            print(f"🎨 Template engine initialized with {len(self.template_dirs)} template directories")
    
    def _setup_template_directories(self):
        """Set up template directories in priority order."""
        
        # Priority 1: Custom templates directory
        if self.config.custom_templates_dir:
            self.template_dirs.append(str(self.config.custom_templates_dir))
            if self.config.verbose:
                print(f"  📁 Custom templates: {self.config.custom_templates_dir}")
        
        # Priority 2: Extract templates from reference lesson
        if self.config.reference_lesson_dir:
            try:
                self.extracted_templates = extract_templates_from_reference(
                    self.config.reference_lesson_dir, 
                    self.config
                )
                
                if self.extracted_templates:
                    # Create temporary directory for extracted templates
                    self.temp_templates_dir = Path(tempfile.mkdtemp(prefix="lesson_gen_templates_"))
                    
                    # Write extracted templates to temp directory
                    for template_name, template_content in self.extracted_templates.items():
                        template_path = self.temp_templates_dir / template_name
                        template_path.write_text(template_content, encoding='utf-8')
                    
                    self.template_dirs.append(str(self.temp_templates_dir))
                    if self.config.verbose:
                        print(f"  📁 Extracted templates: {self.temp_templates_dir} ({len(self.extracted_templates)} templates)")
                
            except Exception as e:
                if self.config.verbose:
                    print(f"  ⚠ Failed to extract templates from reference: {e}")
        
        # Priority 3: Built-in templates (always available)
        self.template_dirs.append(str(self.built_in_templates_dir))
        if self.config.verbose:
            print(f"  📁 Built-in templates: {self.built_in_templates_dir}")
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of template file (e.g., "readme.md.j2")
            context: Template context variables
            
        Returns:
            Rendered template content
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        
        except Exception as e:
            if self.config.verbose:
                print(f"  ⚠ Template rendering failed for {template_name}: {e}")
            
            # Fallback to simple template if rendering fails
            return self._create_fallback_content(template_name, context)
    
    def render_string_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Render a template from string content.
        
        Args:
            template_content: Template content as string
            context: Template context variables
            
        Returns:
            Rendered content
        """
        try:
            template = Template(template_content, environment=self.env)
            return template.render(**context)
        except Exception as e:
            if self.config.verbose:
                print(f"  ⚠ String template rendering failed: {e}")
            return template_content
    
    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template exists in any template directory.
        
        Args:
            template_name: Name of the template to check
            
        Returns:
            True if template exists, False otherwise
        """
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False
    
    def has_custom_templates(self) -> bool:
        """
        Check if custom templates directory exists and has templates.
        
        Returns:
            True if custom templates are available, False otherwise
        """
        if not self.config.custom_templates_dir:
            return False
        
        custom_dir = Path(self.config.custom_templates_dir)
        if not custom_dir.exists():
            return False
        
        # Check if there are any .j2 files in custom templates directory
        return len(list(custom_dir.glob("**/*.j2"))) > 0
    
    def get_template_source(self) -> str:
        """
        Get description of the template source being used.
        
        Returns:
            Human-readable description of template source
        """
        sources = []
        
        if self.config.custom_templates_dir and Path(self.config.custom_templates_dir).exists():
            custom_count = len(list(Path(self.config.custom_templates_dir).glob("**/*.j2")))
            if custom_count > 0:
                sources.append(f"custom ({custom_count} templates)")
        
        if hasattr(self, 'extracted_templates_dir') and self.extracted_templates_dir:
            extracted_count = len(list(self.extracted_templates_dir.glob("**/*.j2")))
            if extracted_count > 0:
                sources.append(f"extracted ({extracted_count} templates)")
        
        builtin_dir = Path(__file__).parent / "templates"
        if builtin_dir.exists():
            builtin_count = len(list(builtin_dir.glob("**/*.j2")))
            if builtin_count > 0:
                sources.append(f"built-in ({builtin_count} templates)")
        
        return " > ".join(sources) if sources else "no templates available"
    
    def extract_templates_from_reference(self, reference_lesson_dir: Path):
        """
        Extract templates from a reference lesson directory.
        
        Args:
            reference_lesson_dir: Path to reference lesson directory
        """
        extractor = TemplateExtractor(self.config)
        templates_dir = extractor.extract_from_directory(reference_lesson_dir)
        
        # Store reference to extracted templates directory
        self.extracted_templates_dir = templates_dir
        
        # Reinitialize the Jinja2 environment with new template directories
        self._setup_template_directories()
    
    def get_available_templates(self) -> Dict[str, str]:
        """
        Get list of all available templates with their sources.
        
        Returns:
            Dictionary mapping template names to their source directories
        """
        templates = {}
        
        for template_dir in self.template_dirs:
            template_path = Path(template_dir)
            if template_path.exists():
                for template_file in template_path.glob("*.j2"):
                    if template_file.name not in templates:  # First found wins (priority)
                        source = "custom" if template_dir == str(self.config.custom_templates_dir) else \
                                "extracted" if hasattr(self, 'temp_templates_dir') and template_dir == str(self.temp_templates_dir) else \
                                "built-in"
                        templates[template_file.name] = source
        
        return templates
    
    def _create_fallback_content(self, template_name: str, context: Dict[str, Any]) -> str:
        """Create fallback content when template rendering fails."""
        
        # Basic fallback templates
        fallbacks = {
            "readme.md.j2": self._fallback_readme,
            "learning_path.md.j2": self._fallback_learning_path,
            "assignment.py.j2": self._fallback_assignment,
            "test_template.py.j2": self._fallback_test,
            "extra_exercises.md.j2": self._fallback_exercises
        }
        
        fallback_func = fallbacks.get(template_name, self._fallback_generic)
        return fallback_func(context)
    
    def _fallback_readme(self, context: Dict[str, Any]) -> str:
        """Fallback README template."""
        topic = context.get('topic', {})
        return f"""# {topic.get('name', 'Lesson Title')}

{topic.get('description', 'Lesson description goes here.')}

## Learning Objectives

{chr(10).join(f"- {obj}" for obj in topic.get('learning_objectives', ['Learn key concepts']))}

## Getting Started

1. Follow the module sequence
2. Complete all assignments
3. Run tests regularly
4. Apply concepts to projects

Generated by lesson-generator v0.1.0
"""
    
    def _fallback_learning_path(self, context: Dict[str, Any]) -> str:
        """Fallback learning path template."""
        module = context.get('module', {})
        return f"""# {module.get('name', 'Module Name')} - Learning Path

## Learning Objectives

Complete this module to understand the key concepts.

## Getting Started

1. Review the starter example
2. Complete the assignments
3. Test your understanding

## Success Criteria

- [ ] Complete all assignments
- [ ] Pass all tests
- [ ] Understand key concepts
"""
    
    def _fallback_assignment(self, context: Dict[str, Any]) -> str:
        """Fallback assignment template."""
        module = context.get('module', {})
        assignment_type = context.get('assignment_type', 'assignment')
        
        return f'''"""
{assignment_type.title()}: {module.get('name', 'Module')}
"""


class ExampleClass:
    """Example class for the assignment."""
    
    def __init__(self):
        """Initialize the class."""
        pass
    
    def example_method(self, param):
        """Example method."""
        return param


if __name__ == "__main__":
    example = ExampleClass()
    print(example.example_method("test"))
'''
    
    def _fallback_test(self, context: Dict[str, Any]) -> str:
        """Fallback test template."""
        return '''"""
Test file template
"""

import pytest


class TestExample:
    """Example test class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        pass
    
    def test_example(self):
        """Example test method."""
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
    
    def _fallback_exercises(self, context: Dict[str, Any]) -> str:
        """Fallback exercises template."""
        module = context.get('module', {})
        return f"""# Extra Exercises: {module.get('name', 'Module')}

## Practice Exercises

### Exercise 1: Basic Practice
Apply the concepts from this module.

### Exercise 2: Intermediate Challenge  
Extend the concepts to more complex scenarios.

### Exercise 3: Advanced Application
Create a real-world application.

## Testing
Run your solutions and verify they work correctly.
"""
    
    def _fallback_generic(self, context: Dict[str, Any]) -> str:
        """Generic fallback template."""
        return f"""# Generated Content

This content was generated automatically.

Context: {context}
"""
    
    @staticmethod
    def _snake_case_filter(text: str) -> str:
        """Convert text to snake_case."""
        import re
        # Replace spaces and hyphens with underscores
        text = re.sub(r'[\s\-]+', '_', text)
        # Convert camelCase to snake_case
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
        # Convert to lowercase and clean up
        text = text.lower()
        text = re.sub(r'[^a-z0-9_]', '', text)
        text = re.sub(r'_+', '_', text)
        return text.strip('_')
    
    @staticmethod
    def _title_case_filter(text: str) -> str:
        """Convert text to Title Case."""
        return text.replace('_', ' ').replace('-', ' ').title()
    
    def cleanup(self):
        """Clean up temporary resources."""
        if hasattr(self, 'temp_templates_dir') and self.temp_templates_dir.exists():
            shutil.rmtree(self.temp_templates_dir)
            if self.config.verbose:
                print(f"🧹 Cleaned up temporary templates directory")
    
    def __del__(self):
        """Destructor to clean up resources."""
        try:
            self.cleanup()
        except:
            pass