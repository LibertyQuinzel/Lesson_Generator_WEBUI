"""
Lesson Generator - AI-powered lesson generation for programming courses.

This package provides tools to automatically generate comprehensive programming
lessons from topic descriptions using OpenAI's API and customizable templates.
"""

__version__ = "0.1.0"
__author__ = "LibertyQuinzel"
__email__ = "your-email@example.com"

# Import main classes (will be available once implemented)
try:
    from .core import LessonGenerator
    from .cli import main
    __all__ = ["LessonGenerator", "main"]
except ImportError:
    # During development, some modules may not be complete
    __all__ = []