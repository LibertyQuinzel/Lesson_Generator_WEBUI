"""
Template extraction system.

This module can read reference lesson directories and automatically extract
Jinja2 templates from existing lesson content. It analyzes patterns in the
reference content to create reusable templates.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import ast

from .models import GenerationConfig


class TemplateExtractor:
    """
    Extracts templates from reference lesson directories.
    
    This class analyzes existing lesson content and creates Jinja2 templates
    that can be used to generate similar content for new topics.
    """
    
    def __init__(self, config: GenerationConfig):
        """
        Initialize the template extractor.
        
        Args:
            config: Generation configuration
        """
        self.config = config
        self.extracted_templates = {}
    
    def extract_templates_from_reference(self, reference_dir: Path) -> Dict[str, str]:
        """
        Extract templates from a reference lesson directory.
        
        Args:
            reference_dir: Path to reference lesson directory
            
        Returns:
            Dictionary mapping template names to template content
        """
        if not reference_dir.exists():
            raise ValueError(f"Reference directory not found: {reference_dir}")
        
        templates = {}
        
        if self.config.verbose:
            print(f"🔍 Extracting templates from: {reference_dir}")
        
        # Extract main README template
        readme_path = reference_dir / "README.md"
        if readme_path.exists():
            templates["readme.md.j2"] = self._extract_readme_template(readme_path)
            if self.config.verbose:
                print("  ✓ Extracted README template")
        
        # Extract module templates from first module directory
        module_dirs = [d for d in reference_dir.iterdir() if d.is_dir() and d.name.startswith("module_")]
        
        if module_dirs:
            first_module = module_dirs[0]
            
            # Extract learning path template
            learning_path = first_module / "learning_path.md"
            if learning_path.exists():
                templates["learning_path.md.j2"] = self._extract_learning_path_template(learning_path)
                if self.config.verbose:
                    print("  ✓ Extracted learning path template")
            
            # Extract starter example template
            starter_example = first_module / "starter_example.py"
            if starter_example.exists():
                templates["starter_example.py.j2"] = self._extract_python_template(starter_example, "starter_example")
                if self.config.verbose:
                    print("  ✓ Extracted starter example template")
            
            # Extract assignment templates
            assignment_a = first_module / "assignment_a.py"
            if assignment_a.exists():
                templates["assignment_a.py.j2"] = self._extract_python_template(assignment_a, "assignment_a")
                if self.config.verbose:
                    print("  ✓ Extracted assignment A template")
            
            assignment_b = first_module / "assignment_b.py"
            if assignment_b.exists():
                templates["assignment_b.py.j2"] = self._extract_python_template(assignment_b, "assignment_b")
                if self.config.verbose:
                    print("  ✓ Extracted assignment B template")
            
            # Extract test templates
            test_files = {
                "test_starter_example.py": "test_starter.py.j2",
                "test_assignment_a.py": "test_assignment_a.py.j2",
                "test_assignment_b.py": "test_assignment_b.py.j2"
            }
            
            for test_file, template_name in test_files.items():
                test_path = first_module / test_file
                if test_path.exists():
                    templates[template_name] = self._extract_test_template(test_path, test_file)
                    if self.config.verbose:
                        print(f"  ✓ Extracted {test_file} template")
            
            # Extract extra exercises template
            extra_exercises = first_module / "extra_exercises.md"
            if extra_exercises.exists():
                templates["extra_exercises.md.j2"] = self._extract_extra_exercises_template(extra_exercises)
                if self.config.verbose:
                    print("  ✓ Extracted extra exercises template")
        
        # Extract configuration file templates
        config_files = {
            "requirements.txt": "requirements.txt.j2",
            "pytest.ini": "pytest.ini.j2",
            "Makefile": "Makefile.j2",
            "setup.cfg": "setup.cfg.j2"
        }
        
        for config_file, template_name in config_files.items():
            config_path = reference_dir / config_file
            if config_path.exists():
                templates[template_name] = self._extract_config_template(config_path)
                if self.config.verbose:
                    print(f"  ✓ Extracted {config_file} template")
        
        self.extracted_templates = templates
        if self.config.verbose:
            print(f"📝 Extracted {len(templates)} templates total")
        
        return templates
    
    def _extract_readme_template(self, readme_path: Path) -> str:
        """Extract README template with Jinja2 variables."""
        content = readme_path.read_text(encoding='utf-8')
        
        # Replace specific content with template variables
        template_content = content
        
        # Replace title (usually first # heading)
        template_content = re.sub(
            r'^# (.+?)$',
            '# {{ topic.name }}',
            template_content,
            flags=re.MULTILINE
        )
        
        # Replace description paragraphs
        lines = template_content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            # Replace course overview section
            if line.startswith('A comprehensive lesson on') or line.startswith('This course covers'):
                new_lines.append('{{ topic.description }}')
            # Replace estimated hours
            elif 'hours to complete' in line.lower():
                new_lines.append('This lesson should take approximately {{ topic.estimated_hours }} hours to complete.')
            # Replace learning objectives
            elif line.strip() and i > 0 and ('learning objectives' in lines[i-1].lower() or 'you will learn' in lines[i-1].lower()):
                if line.startswith('- '):
                    # Start of learning objectives list
                    new_lines.append('{% for objective in topic.learning_objectives %}')
                    new_lines.append('- {{ objective }}')
                    new_lines.append('{% endfor %}')
                    # Skip until end of list
                    j = i + 1
                    while j < len(lines) and (lines[j].startswith('- ') or lines[j].strip() == ''):
                        j += 1
                    i = j - 1
                else:
                    new_lines.append(line)
            # Replace prerequisites section
            elif 'prerequisites' in line.lower() and line.startswith('#'):
                new_lines.append(line)
                new_lines.append('')
                new_lines.append('{% if topic.prerequisites %}')
                new_lines.append('{% for prereq in topic.prerequisites %}')
                new_lines.append('- {{ prereq }}')
                new_lines.append('{% endfor %}')
                new_lines.append('{% else %}')
                new_lines.append('None')
                new_lines.append('{% endif %}')
                # Skip existing prerequisites
                j = i + 1
                while j < len(lines) and not lines[j].startswith('#'):
                    j += 1
                i = j - 1
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _extract_learning_path_template(self, learning_path: Path) -> str:
        """Extract learning path template."""
        content = learning_path.read_text(encoding='utf-8')
        
        # Replace module-specific content with template variables
        template_content = content
        
        # Replace title
        template_content = re.sub(
            r'^# Module \d+: (.+?) - (.+?)$',
            '# {{ module.name }} - Learning Path',
            template_content,
            flags=re.MULTILINE
        )
        
        # Replace learning objectives section
        template_content = re.sub(
            r'By the end of this module, you will understand:\n(- .+?\n)+',
            '''By the end of this module, you will understand:
{% for objective in learning_objectives %}
- {{ objective }}
{% endfor %}

''',
            template_content,
            flags=re.DOTALL
        )
        
        # Replace concepts section  
        template_content = re.sub(
            r'(### Key Concepts.*?\n)(.*?)(?=\n###|\n##|$)',
            r'\1{% for concept in concepts %}\n- **{{ concept|title }}**: {{ concept_descriptions[concept] if concept_descriptions else "Core concept in " + topic.name.lower() }}\n{% endfor %}',
            template_content,
            flags=re.DOTALL
        )
        
        return template_content
    
    def _extract_python_template(self, python_path: Path, template_type: str) -> str:
        """Extract Python code template."""
        content = python_path.read_text(encoding='utf-8')
        
        # Parse the Python file to understand its structure
        try:
            tree = ast.parse(content)
            
            # Extract class and method information
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'docstring': ast.get_docstring(node),
                        'methods': []
                    }
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                'name': item.name,
                                'docstring': ast.get_docstring(item),
                                'args': [arg.arg for arg in item.args.args[1:]]  # Skip 'self'
                            }
                            class_info['methods'].append(method_info)
                    
                    classes.append(class_info)
            
            # Generate template based on structure
            if classes:
                return self._generate_python_template(classes[0], template_type, content)
        
        except SyntaxError:
            # If parsing fails, create a basic template
            pass
        
        # Fallback: create basic template with variable substitution
        template_content = content
        
        # Replace class names with template variables
        template_content = re.sub(
            r'class (\w+):',
            'class {{ class_name }}:',
            template_content
        )
        
        # Replace docstrings with template variables
        template_content = re.sub(
            r'"""([^"]+?)"""',
            r'"""\n{% if description %}{{ description }}{% else %}\1{% endif %}\n"""',
            template_content,
            count=1
        )
        
        return template_content
    
    def _generate_python_template(self, class_info: Dict, template_type: str, original_content: str) -> str:
        """Generate Python template from class information."""
        
        template_lines = [
            '"""',
            f'{{% if description %}}{{{{ description }}}}{{% else %}}{template_type.replace("_", " ").title()}: {{{{ module.name }}}}{{% endif %}}',
            '"""',
            '',
            '',
            'class {{ class_name if class_name else "' + class_info['name'] + '" }}:',
            '    """',
            f'    {{% if class_description %}}{{{{ class_description }}}}{{% else %}}{class_info["docstring"] or f"Class for {template_type.replace("_", " ")}"}{{% endif %}}',
            '    """',
            ''
        ]
        
        # Add methods
        for method in class_info['methods']:
            template_lines.extend([
                f'    def {method["name"]}(self{", " + ", ".join(method["args"]) if method["args"] else ""}):',
                '        """',
                f'        {{% if {method["name"]}_description %}}{{{{ {method["name"]}_description }}}}{{% else %}}{method["docstring"] or f"Method: {method["name"]}"}{{% endif %}}',
                '        """',
                f'        # TODO: Implement {method["name"]}',
                '        pass',
                ''
            ])
        
        # Add usage example for starter examples
        if template_type == "starter_example":
            template_lines.extend([
                '',
                'if __name__ == "__main__":',
                '    {{ usage_example if usage_example else "# Example usage here" }}'
            ])
        
        return '\n'.join(template_lines)
    
    def _extract_test_template(self, test_path: Path, test_type: str) -> str:
        """Extract test template."""
        content = test_path.read_text(encoding='utf-8')
        
        template_content = content
        
        # Replace imports with template variables
        template_content = re.sub(
            r'from (\w+) import (\w+)',
            r'from {{ module_file if module_file else "\1" }} import {{ class_name if class_name else "\2" }}',
            template_content
        )
        
        # Replace class names in test classes
        template_content = re.sub(
            r'class Test(\w+):',
            r'class Test{{ class_name if class_name else "\1" }}:',
            template_content
        )
        
        # Replace instance creation
        template_content = re.sub(
            r'self\.(\w+) = (\w+)\(\)',
            r'self.{{ instance_name if instance_name else "\1" }} = {{ class_name if class_name else "\2" }}()',
            template_content
        )
        
        return template_content
    
    def _extract_extra_exercises_template(self, exercises_path: Path) -> str:
        """Extract extra exercises template."""
        content = exercises_path.read_text(encoding='utf-8')
        
        # Replace title with template variable
        template_content = re.sub(
            r'^# Extra Exercises: (.+?)$',
            '# Extra Exercises: {{ module.name }}',
            content,
            flags=re.MULTILINE
        )
        
        # Replace module-specific references
        template_content = re.sub(
            r'Practice and reinforce (.+?) concepts',
            'Practice and reinforce {{ ", ".join(module.focus_areas) }} concepts',
            template_content
        )
        
        return template_content
    
    def _extract_config_template(self, config_path: Path) -> str:
        """Extract configuration file template."""
        content = config_path.read_text(encoding='utf-8')
        
        # For most config files, we can use them as-is or with minimal templating
        if config_path.name == "requirements.txt":
            # Add comment header
            template_content = f"# Requirements for {{ topic.name }}\n# Generated by lesson-generator\n\n{content}"
        else:
            template_content = content
        
        return template_content
    
    def save_extracted_templates(self, output_dir: Path) -> None:
        """
        Save extracted templates to directory.
        
        Args:
            output_dir: Directory to save templates in
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for template_name, template_content in self.extracted_templates.items():
            template_path = output_dir / template_name
            template_path.write_text(template_content, encoding='utf-8')
            
            if self.config.verbose:
                print(f"💾 Saved template: {template_name}")
        
        if self.config.verbose:
            print(f"📁 All templates saved to: {output_dir}")


def extract_templates_from_reference(reference_dir: Path, config: GenerationConfig) -> Dict[str, str]:
    """
    Convenience function to extract templates from reference directory.
    
    Args:
        reference_dir: Path to reference lesson directory
        config: Generation configuration
        
    Returns:
        Dictionary of extracted templates
    """
    extractor = TemplateExtractor(config)
    return extractor.extract_templates_from_reference(reference_dir)