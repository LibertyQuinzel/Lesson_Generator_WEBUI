"""
Command Line Interface for the Lesson Generator.

This module provides the main CLI entry point using Click framework.
It handles command parsing, validation, and orchestrates the lesson generation process.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

import click
from dotenv import load_dotenv

from .models import TopicConfig, GenerationConfig
from .core import LessonGenerator
from .utils.validation import validate_topic, validate_output_path


# Load environment variables from .env file
load_dotenv()


@click.group()
@click.version_option(version="0.1.0", prog_name="lesson-generator")
def cli():
    """
    AI-powered lesson generator for programming courses.
    
    Generate comprehensive programming lessons from topic descriptions using
    OpenAI's API and customizable templates.
    """
    pass


@cli.command()
@click.argument('topics', nargs=-1, required=True)
@click.option(
    '--output', '-o',
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=Path('./generated_lessons'),
    help='Output directory for generated lessons'
)
@click.option(
    '--modules', '-m',
    type=click.IntRange(1, 10),
    default=None,
    help='Number of modules per lesson (1-10). If omitted, must be provided via --config file.'
)
@click.option(
    '--difficulty', '-d',
    type=click.Choice(['beginner', 'intermediate', 'advanced'], case_sensitive=False),
    default='intermediate',
    help='Target difficulty level'
)
@click.option(
    '--beginner', '-b',
    'difficulty_shortcut',
    flag_value='beginner',
    help='Shortcut for --difficulty beginner'
)
@click.option(
    '--intermediate', '-i',
    'difficulty_shortcut', 
    flag_value='intermediate',
    help='Shortcut for --difficulty intermediate'
)
@click.option(
    '--advanced', '-a',
    'difficulty_shortcut',
    flag_value='advanced', 
    help='Shortcut for --difficulty advanced'
)
@click.option(
    '--config',
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help='Path to topic configuration JSON file'
)
@click.option(
    '--openai-api-key',
    envvar='OPENAI_API_KEY',
    help='OpenAI API key (or set OPENAI_API_KEY env var)'
)
@click.option(
    '--no-ai',
    is_flag=True,
    default=False,
    help='Use deterministic content generation without AI'
)
@click.option(
    '--strict-ai/--no-strict-ai',
    default=True,
    help='Require AI for all content (default: strict)'
)
@click.option(
    '--cost-efficient',
    is_flag=True,
    default=False,
    help='Use cost-optimized AI settings (GPT-3.5-turbo, reduced tokens)'
)
@click.option(
    '--workers',
    type=click.IntRange(1, 8),
    default=1,
    help='Number of parallel workers for processing'
)
@click.option(
    '--templates',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help='Custom templates directory to override defaults'
)
@click.option(
    '--reference',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help='Reference lesson directory to extract templates from'
)
@click.option(
    '--cache/--no-cache',
    default=True,
    help='Enable/disable generation cache (default: enabled)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    default=False,
    help='Enable verbose output'
)
def create(
    topics: tuple,
    output: Path,
    modules: Optional[int],
    difficulty: str,
    difficulty_shortcut: Optional[str],
    config: Optional[Path],
    openai_api_key: Optional[str],
    no_ai: bool,
    strict_ai: bool,
    cost_efficient: bool,
    workers: int,
    templates: Optional[Path],
    reference: Optional[Path],
    cache: bool,
    verbose: bool
) -> None:
    """
    Create lessons from topic names or configuration file.
    
    TOPICS: Space-separated list of topic names (e.g., async_programming design_patterns)
    
    Examples:
    
        # Generate single lesson
        lesson-generator create async_programming --output ./lessons
        
        # Generate multiple lessons with custom difficulty
        lesson-generator create async_programming design_patterns --difficulty advanced
        
        # Use configuration file
        lesson-generator create --config topics.json
        
        # Generate without AI (deterministic content)
        lesson-generator create async_programming --no-ai
    """
    
    # Resolve difficulty (shortcuts override main option)
    final_difficulty = difficulty_shortcut or difficulty
    
    # Validate AI configuration
    if not no_ai and strict_ai and not openai_api_key:
        click.echo(click.style(
            "Error: OpenAI API key required for AI-powered generation. "
            "Set OPENAI_API_KEY environment variable or use --openai-api-key option. "
            "Alternatively, use --no-ai for deterministic generation.",
            fg='red'
        ), err=True)
        sys.exit(1)
    
    # Validate output path
    try:
        validate_output_path(output)
    except ValueError as e:
        click.echo(click.style(f"Error: {e}", fg='red'), err=True)
        sys.exit(1)
    
    # Apply cost-efficient settings if requested
    if cost_efficient and not no_ai:
        # Force GPT-3.5-turbo for cost efficiency
        openai_model = "gpt-3.5-turbo"
        rate_limit_delay = 0.5  # Shorter delay for faster processing
        if verbose:
            click.echo("💰 Cost-efficient mode enabled: Using GPT-3.5-turbo with reduced token limits")
    else:
        openai_model = "gpt-4"
        rate_limit_delay = 1.0
    
    # Set up generation configuration
    generation_config = GenerationConfig(
        output_dir=output,
        modules_count=modules,
        difficulty=final_difficulty,
        use_ai=not no_ai,
        strict_ai=strict_ai,
        workers=workers,
        custom_templates_dir=templates,
        reference_lesson_dir=reference,
        enable_cache=cache,
        verbose=verbose,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        rate_limit_delay=rate_limit_delay
    )
    
    # Determine topics to process
    topics_to_process = []
    
    if config:
        # Load topics from configuration file
        try:
            topics_to_process = load_topics_from_config(config)
        except Exception as e:
            click.echo(click.style(f"Error loading config file: {e}", fg='red'), err=True)
            sys.exit(1)
    else:
        # Create topics from command line arguments
        # If CLI topics are provided, require explicit modules count (no default)
        if modules is None:
            click.echo(click.style(
                "Error: --modules is required when creating topics on the command line without --config.\n"
                "Provide --modules N (1-10) or use --config to load topic definitions.",
                fg='red'
            ), err=True)
            sys.exit(1)
        for topic_name in topics:
            try:
                topic_config = create_topic_from_name(topic_name, final_difficulty, modules)
                validate_topic(topic_config)
                topics_to_process.append(topic_config)
            except ValueError as e:
                click.echo(click.style(f"Error with topic '{topic_name}': {e}", fg='red'), err=True)
                sys.exit(1)
    
    if not topics_to_process:
        click.echo(click.style("Error: No valid topics to process", fg='red'), err=True)
        sys.exit(1)
    
    # Initialize lesson generator
    try:
        generator = LessonGenerator(generation_config)
    except Exception as e:
        click.echo(click.style(f"Error initializing generator: {e}", fg='red'), err=True)
        sys.exit(1)
    
    # Progress reporting
    if verbose:
        click.echo(f"Generating {len(topics_to_process)} lesson(s):")
        for topic in topics_to_process:
            click.echo(f"  - {topic.name} ({topic.difficulty})")
        click.echo(f"Output directory: {output}")
        click.echo(f"AI enabled: {not no_ai}")
        click.echo()
    
    # Generate lessons
    total_lessons = len(topics_to_process)
    success_count = 0
    
    with click.progressbar(topics_to_process, label='Generating lessons') as topics_progress:
        for topic in topics_progress:
            try:
                if verbose:
                    click.echo(f"\nProcessing: {topic.name}")
                
                result = generator.generate_lesson(topic)
                
                if result.success:
                    success_count += 1
                    if verbose:
                        click.echo(click.style(f"✓ Generated: {topic.name}", fg='green'))
                else:
                    if verbose:
                        click.echo(click.style(f"✗ Failed: {topic.name} - {result.error}", fg='red'))
                    
            except Exception as e:
                if verbose:
                    click.echo(click.style(f"✗ Error processing {topic.name}: {e}", fg='red'))
    
    # Final summary
    click.echo()
    if success_count == total_lessons:
        click.echo(click.style(
            f"✓ Successfully generated all {total_lessons} lesson(s) in {output}",
            fg='green'
        ))
    else:
        failed_count = total_lessons - success_count
        click.echo(click.style(
            f"Generated {success_count}/{total_lessons} lessons. {failed_count} failed.",
            fg='yellow' if success_count > 0 else 'red'
        ))
        click.echo(f"Check individual error logs in the output directory for details.")


def load_topics_from_config(config_path: Path) -> List[TopicConfig]:
    """Load and validate topics from configuration file."""
    # Implementation will be added in next iteration
    raise NotImplementedError("Configuration file loading not yet implemented")


def create_topic_from_name(topic_name: str, difficulty: str, modules_count: int) -> TopicConfig:
    """Create a topic configuration from a simple topic name."""
    print(f"🔧 DEBUG CLI: create_topic_from_name called with topic='{topic_name}', difficulty='{difficulty}', modules_count={modules_count}")
    from .utils.validation import validate_topic_name, create_slug_from_name
    from .models import TopicConfig, ModuleConfig, DifficultyLevel, ModuleType, CodeComplexity
    
    # Validate and normalize topic name
    normalized_name = validate_topic_name(topic_name)
    slug = create_slug_from_name(normalized_name)
    
    # Create basic topic description
    description = f"A comprehensive lesson on {normalized_name.lower()} concepts and practical applications."
    
    # Generate basic concepts based on topic name
    concepts = [
        f"{normalized_name.lower()} fundamentals",
        "practical applications",
        "best practices",
        "real-world examples"
    ]
    
    # Create learning objectives
    learning_objectives = [
        f"Understand core concepts of {normalized_name.lower()}",
        f"Apply {normalized_name.lower()} techniques effectively",
        f"Implement {normalized_name.lower()} solutions to real problems",
        f"Follow best practices in {normalized_name.lower()}"
    ]
    
    # Determine estimated hours based on difficulty
    hours_map = {
        "beginner": 4.0,
        "intermediate": 6.0,
        "advanced": 8.0
    }
    estimated_hours = hours_map.get(difficulty, 6.0)
    
    # Create modules based on requested count
    modules = []
    
    # Validate modules_count
    if modules_count < 1:
        modules_count = 1
    
    # For single module, create just one starter module
    if modules_count == 1:
        print(f"🔧 DEBUG CLI: Creating single module for {normalized_name}")
        modules.append(ModuleConfig(
            name=f"{normalized_name} Overview",
            type=ModuleType.STARTER,
            focus_areas=["core concepts", "overview", "practical examples"],
            code_complexity=CodeComplexity.SIMPLE
        ))
        print(f"🔧 DEBUG CLI: Single module created: {modules[0].name}")
    else:
        print(f"🔧 DEBUG CLI: Creating {modules_count} modules for {normalized_name}")
        # Always start with a starter module for multi-module lessons
        modules.append(ModuleConfig(
            name=f"{normalized_name} Fundamentals",
            type=ModuleType.STARTER,
            focus_areas=["basic concepts", "introduction", "setup"],
            code_complexity=CodeComplexity.SIMPLE
        ))
        
        # Add assignment modules and project module to reach requested count
        complexity_map = {
            "beginner": CodeComplexity.SIMPLE,
            "intermediate": CodeComplexity.MODERATE,
            "advanced": CodeComplexity.COMPLEX
        }
        default_complexity = complexity_map.get(difficulty, CodeComplexity.MODERATE)
        
        # Add assignment modules (leave room for project module if needed)
        assignment_count = modules_count - 1  # Subtract starter module
        if modules_count >= 4:
            assignment_count -= 1  # Leave room for project module
        
        for i in range(assignment_count):
            modules.append(ModuleConfig(
                name=f"{normalized_name} Implementation {i+1}",
                type=ModuleType.ASSIGNMENT,
                focus_areas=[f"implementation {i+1}", "practical exercises"],
                code_complexity=default_complexity
            ))
        
        # Add a final project module if we have enough modules
        if modules_count >= 4:
            modules.append(ModuleConfig(
                name=f"{normalized_name} Project",
                type=ModuleType.PROJECT,
                focus_areas=["project implementation", "integration", "real-world application"],
                code_complexity=CodeComplexity.COMPLEX
            ))
    
    # Create and return topic configuration
    print(f"🔧 DEBUG CLI: Final modules list has {len(modules)} modules: {[m.name for m in modules]}")
    topic_config = TopicConfig(
        name=normalized_name,
        slug=slug,
        description=description,
        difficulty=DifficultyLevel(difficulty),
        estimated_hours=estimated_hours,
        concepts=concepts,
        learning_objectives=learning_objectives,
        prerequisites=[],  # Empty for generated topics
        modules=modules
    )
    print(f"🔧 DEBUG CLI: Returning topic config with {len(topic_config.modules)} modules")
    return topic_config


@cli.command()
def version():
    """Show version information."""
    click.echo("lesson-generator version 0.1.0")


@cli.command()
@click.argument('lesson_path', type=click.Path(exists=True, path_type=Path))
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
def validate(lesson_path: Path, verbose: bool):
    """
    Validate the quality of a generated lesson.
    
    LESSON_PATH: Path to the lesson directory to validate
    
    Examples:
        lesson-generator validate ./generated_lessons/python_fundamentals
        lesson-generator validate ./my_lesson --verbose
    """
    from .quality import QualityAssurance
    from .models import GenerationConfig
    
    try:
        # Create minimal config for quality assurance
        config = GenerationConfig(
            output_dir=lesson_path.parent,
            verbose=verbose
        )
        
        qa = QualityAssurance(config)
        report = qa.validate_lesson(lesson_path)
        
        # Print results
        if report.quality_score >= 0.8:
            click.echo(click.style(f"✓ Excellent quality: {report.quality_score:.2f}/1.0", fg='green'))
        elif report.quality_score >= 0.6:
            click.echo(click.style(f"⚠ Good quality: {report.quality_score:.2f}/1.0", fg='yellow'))
        else:
            click.echo(click.style(f"✗ Poor quality: {report.quality_score:.2f}/1.0", fg='red'))
        
        if report.issues:
            click.echo("\nIssues found:")
            for issue in report.issues:
                click.echo(f"  - {issue}")
        
        # Exit with appropriate code
        sys.exit(0 if report.quality_score >= 0.6 else 1)
        
    except Exception as e:
        click.echo(click.style(f"Validation failed: {e}", fg='red'), err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--output', '-o',
    type=click.Path(exists=False, file_okay=True, dir_okay=False, path_type=Path),
    default=Path('.env'),
    help='Output file for environment template'
)
def init_env(output: Path):
    """Initialize environment file with template."""
    template = '''# Lesson Generator Environment Configuration

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Development Settings  
DEBUG=False
LOG_LEVEL=INFO

# Default Settings
# DEFAULT_OUTPUT_DIR=./generated_lessons
'''
    
    if output.exists():
        if not click.confirm(f"File {output} exists. Overwrite?"):
            return
    
    output.write_text(template)
    click.echo(f"Environment template written to {output}")
    click.echo("Please edit the file and add your OpenAI API key.")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()