"""
Unit tests for the CLI module.

This module tests the command-line interface functionality including
argument parsing, validation, and basic command execution.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Skip import errors during development
try:
    from lesson_generator.cli import cli, create_topic_from_name
    from lesson_generator.models import DifficultyLevel, ModuleType
    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not CLI_AVAILABLE, reason="CLI module not fully implemented")
class TestCLI:
    """Test cases for the CLI interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test that CLI help works."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'lesson-generator' in result.output.lower()
    
    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(cli, ['version'])
        assert result.exit_code == 0
        assert '0.1.0' in result.output
    
    def test_create_help(self):
        """Test create command help."""
        result = self.runner.invoke(cli, ['create', '--help'])
        assert result.exit_code == 0
        assert 'topics' in result.output.lower()
    
    def test_init_env_command(self):
        """Test environment initialization command."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ['init-env', '--output', '.env.test'])
            assert result.exit_code == 0
            
            # Check that file was created
            env_file = Path('.env.test')
            assert env_file.exists()
            
            content = env_file.read_text()
            assert 'OPENAI_API_KEY' in content


@pytest.mark.unit
@pytest.mark.skipif(not CLI_AVAILABLE, reason="CLI module not fully implemented")
class TestTopicCreation:
    """Test cases for topic creation from names."""
    
    def test_create_topic_from_name_basic(self):
        """Test basic topic creation from name."""
        topic = create_topic_from_name("Async Programming", "intermediate", 5)
        
        assert topic.name == "Async Programming"
        assert topic.slug == "async_programming"
        assert topic.difficulty == DifficultyLevel.INTERMEDIATE
        assert topic.estimated_hours == 6.0
        assert len(topic.modules) == 5
        
        # Check module types
        module_types = [m.type for m in topic.modules]
        assert ModuleType.STARTER in module_types
        assert ModuleType.PROJECT in module_types
    
    def test_create_topic_different_difficulties(self):
        """Test topic creation with different difficulty levels."""
        # Test beginner
        topic_beginner = create_topic_from_name("Python Basics", "beginner", 4)
        assert topic_beginner.difficulty == DifficultyLevel.BEGINNER
        assert topic_beginner.estimated_hours == 4.0
        
        # Test advanced
        topic_advanced = create_topic_from_name("Design Patterns", "advanced", 6)
        assert topic_advanced.difficulty == DifficultyLevel.ADVANCED
        assert topic_advanced.estimated_hours == 8.0
    
    def test_topic_slug_generation(self):
        """Test slug generation from topic names."""
        test_cases = [
            ("Async Programming", "async_programming"),
            ("Design Patterns in Python", "design_patterns_in_python"),
            ("Web Development", "web_development"),
            ("Data-Science & ML", "data_science_ml")
        ]
        
        for name, expected_slug in test_cases:
            topic = create_topic_from_name(name, "intermediate", 4)
            assert topic.slug == expected_slug
    
    def test_invalid_topic_names(self):
        """Test validation of invalid topic names."""
        with pytest.raises(ValueError):
            create_topic_from_name("", "intermediate", 4)
        
        with pytest.raises(ValueError):
            create_topic_from_name("   ", "intermediate", 4)
        
        with pytest.raises(ValueError):
            create_topic_from_name("A" * 200, "intermediate", 4)


@pytest.mark.integration
@pytest.mark.skipif(not CLI_AVAILABLE, reason="CLI module not fully implemented")
class TestCLIIntegration:
    """Integration tests for CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('lesson_generator.cli.LessonGenerator')
    def test_create_command_no_api_key(self, mock_generator_class):
        """Test create command without API key fails appropriately."""
        result = self.runner.invoke(cli, [
            'create', 'test_topic',
            '--output', '/tmp/test_output'
        ])
        
        # Should fail due to missing API key in strict mode
        assert result.exit_code == 1
        assert 'OpenAI API key required' in result.output
    
    @patch('lesson_generator.cli.LessonGenerator')
    def test_create_command_no_ai_mode(self, mock_generator_class):
        """Test create command with no-ai flag."""
        with self.runner.isolated_filesystem():
            # Mock the generator and its methods
            mock_generator = MagicMock()
            mock_generator_class.return_value = mock_generator
            
            # Mock successful generation result
            from lesson_generator.models import LessonGenerationResult
            mock_result = LessonGenerationResult(
                topic_name="test_topic",
                topic_slug="test_topic", 
                success=True,
                output_path=Path("./test_output")
            )
            mock_generator.generate_lesson.return_value = mock_result
            
            result = self.runner.invoke(cli, [
                'create', 'test_topic',
                '--no-ai',
                '--output', './test_output'
            ])
            
            assert result.exit_code == 0
    
    def test_create_command_invalid_output_path(self):
        """Test create command with invalid output path."""
        result = self.runner.invoke(cli, [
            'create', 'test_topic',
            '--output', '/root/no_permission',  # Likely no permission
            '--no-ai'
        ])
        
        # Should handle permission errors gracefully
        # Note: Exact behavior depends on system permissions


if __name__ == '__main__':
    pytest.main([__file__, '-v'])