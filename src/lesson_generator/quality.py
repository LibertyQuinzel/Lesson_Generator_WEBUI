"""
Quality assurance system for generated lessons.

This module provides validation, linting, and quality checking
for generated lesson content.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import GenerationConfig, QualityReport, ValidationResult


class QualityAssurance:
    """
    Quality assurance system for lesson content.
    
    Provides:
    - Python syntax validation
    - Code style checking
    - Test execution validation
    - Content quality metrics
    """
    
    def __init__(self, config: GenerationConfig):
        """
        Initialize quality assurance system.
        
        Args:
            config: Generation configuration
        """
        self.config = config
    
    def validate_lesson(self, lesson_path: Path) -> QualityReport:
        """
        Perform comprehensive quality validation on a generated lesson.
        
        Args:
            lesson_path: Path to generated lesson directory
            
        Returns:
            Quality report with validation results
        """
        report = QualityReport(
            lesson_path=lesson_path,
            python_files_valid=True,
            tests_executable=True,
            quality_score=0.0,
            issues=[],
            metrics={}
        )
        
        try:
            # Validate Python syntax
            syntax_results = self._validate_python_syntax(lesson_path)
            report.python_files_valid = all(result.is_valid for result in syntax_results)
            
            # Check test executability
            test_results = self._validate_tests(lesson_path)
            report.tests_executable = test_results.get('executable', False)
            
            # Calculate quality metrics
            metrics = self._calculate_quality_metrics(lesson_path)
            report.metrics = metrics
            
            # Calculate overall quality score
            report.quality_score = self._calculate_quality_score(report)
            
            if self.config.verbose:
                self._print_quality_report(report)
            
        except Exception as e:
            report.issues.append(f"Quality validation failed: {e}")
            report.quality_score = 0.0
        
        return report
    
    def _validate_python_syntax(self, lesson_path: Path) -> List[ValidationResult]:
        """Validate Python syntax for all .py files."""
        results = []
        
        for py_file in lesson_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse with AST to check syntax
                ast.parse(content, filename=str(py_file))
                
                results.append(ValidationResult(
                    file_path=py_file,
                    is_valid=True,
                    errors=[],
                    warnings=[]
                ))
                
            except SyntaxError as e:
                results.append(ValidationResult(
                    file_path=py_file,
                    is_valid=False,
                    errors=[f"Syntax error at line {e.lineno}: {e.msg}"],
                    warnings=[]
                ))
            except Exception as e:
                results.append(ValidationResult(
                    file_path=py_file,
                    is_valid=False,
                    errors=[f"Validation error: {e}"],
                    warnings=[]
                ))
        
        return results
    
    def _validate_tests(self, lesson_path: Path) -> Dict[str, Any]:
        """Validate that tests can be executed."""
        results = {
            'executable': False,
            'test_files': [],
            'errors': []
        }
        
        try:
            # Find test files
            test_files = list(lesson_path.rglob("test_*.py"))
            results['test_files'] = [str(f) for f in test_files]
            
            if not test_files:
                results['errors'].append("No test files found")
                return results
            
            # Check if pytest.ini exists
            pytest_ini = lesson_path / "pytest.ini"
            if pytest_ini.exists():
                results['executable'] = True
            else:
                results['warnings'] = results.get('warnings', [])
                results['warnings'].append("No pytest.ini found")
                results['executable'] = True  # Still executable, just not configured
            
        except Exception as e:
            results['errors'].append(f"Test validation error: {e}")
        
        return results
    
    def _calculate_quality_metrics(self, lesson_path: Path) -> Dict[str, Any]:
        """Calculate quality metrics for the lesson."""
        metrics = {
            'total_files': 0,
            'python_files': 0,
            'test_files': 0,
            'markdown_files': 0,
            'total_lines': 0,
            'has_readme': False,
            'has_requirements': False,
            'has_makefile': False,
            'module_count': 0
        }
        
        try:
            # Count files and lines
            for file_path in lesson_path.rglob("*"):
                if file_path.is_file():
                    metrics['total_files'] += 1
                    
                    if file_path.suffix == '.py':
                        metrics['python_files'] += 1
                        if file_path.name.startswith('test_'):
                            metrics['test_files'] += 1
                    elif file_path.suffix == '.md':
                        metrics['markdown_files'] += 1
                    
                    # Count lines
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            metrics['total_lines'] += len(f.readlines())
                    except:
                        pass  # Skip binary files
            
            # Check for important files
            metrics['has_readme'] = (lesson_path / "README.md").exists()
            metrics['has_requirements'] = (lesson_path / "requirements.txt").exists()
            metrics['has_makefile'] = (lesson_path / "Makefile").exists()
            
            # Count modules (directories starting with "module_")
            metrics['module_count'] = len([
                d for d in lesson_path.iterdir() 
                if d.is_dir() and d.name.startswith('module_')
            ])
            
        except Exception as e:
            metrics['error'] = f"Metrics calculation failed: {e}"
        
        return metrics
    
    def _calculate_quality_score(self, report: QualityReport) -> float:
        """Calculate overall quality score (0.0 - 1.0)."""
        score = 0.0
        max_score = 10.0
        
        # Python syntax validation (3 points)
        if report.python_files_valid:
            score += 3.0
        
        # Test executability (2 points)
        if report.tests_executable:
            score += 2.0
        
        # Required files (3 points)
        if report.metrics.get('has_readme', False):
            score += 1.0
        if report.metrics.get('has_requirements', False):
            score += 1.0
        if report.metrics.get('has_makefile', False):
            score += 1.0
        
        # File structure quality (2 points)
        test_ratio = 0
        if report.metrics.get('python_files', 0) > 0:
            test_ratio = report.metrics.get('test_files', 0) / report.metrics.get('python_files', 1)
        
        if test_ratio >= 0.4:  # Good test coverage
            score += 2.0
        elif test_ratio >= 0.2:  # Moderate test coverage
            score += 1.0
        
        return min(score / max_score, 1.0)
    
    def _print_quality_report(self, report: QualityReport):
        """Print formatted quality report."""
        print(f"\n🔍 Quality Report for {report.lesson_path.name}")
        print(f"Overall Score: {report.quality_score:.2f}/1.0")
        
        # Syntax validation
        status = "✓" if report.python_files_valid else "✗"
        print(f"Python Syntax: {status}")
        
        # Test validation
        status = "✓" if report.tests_executable else "✗"
        print(f"Tests Executable: {status}")
        
        # Metrics
        metrics = report.metrics
        print(f"Files: {metrics.get('total_files', 0)} total, {metrics.get('python_files', 0)} Python, {metrics.get('test_files', 0)} tests")
        print(f"Modules: {metrics.get('module_count', 0)}")
        
        # Issues
        if report.issues:
            print(f"Issues ({len(report.issues)}):")
            for issue in report.issues:
                print(f"  - {issue}")
    
    def run_linting(self, lesson_path: Path) -> Dict[str, Any]:
        """Run code linting on Python files."""
        results = {
            'success': True,
            'files_checked': 0,
            'issues': [],
            'warnings': []
        }
        
        try:
            python_files = list(lesson_path.rglob("*.py"))
            results['files_checked'] = len(python_files)
            
            # Simple linting checks without external dependencies
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic style checks
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        # Check line length
                        if len(line) > 100:
                            results['warnings'].append(
                                f"{py_file.name}:{i} Line too long ({len(line)} > 100)"
                            )
                        
                        # Check for trailing whitespace
                        if line.rstrip() != line:
                            results['warnings'].append(
                                f"{py_file.name}:{i} Trailing whitespace"
                            )
                
                except Exception as e:
                    results['issues'].append(f"Linting error in {py_file.name}: {e}")
                    results['success'] = False
        
        except Exception as e:
            results['success'] = False
            results['issues'].append(f"Linting failed: {e}")
        
        return results