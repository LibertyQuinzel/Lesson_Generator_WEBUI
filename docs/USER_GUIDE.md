# 📚 Lesson Generator - User Guide

## 🎯 Overview

The Lesson Generator is an AI-powered tool that creates comprehensive programming lessons with exercises, examples, and assessments. This guide covers how to use both the web interface and command-line interface.

## 🌐 Web Interface Guide

### Getting Started

1. **Access the Application**
   - Open your browser to `http://localhost:8000`
   - You'll see the Lesson Generator dashboard

2. **System Status Check**
   - Green indicator: System ready
   - Yellow indicator: Limited functionality
   - Red indicator: System unavailable

### Creating Your First Lesson

#### Step 1: Basic Information
- **Lesson Name**: Enter a descriptive name (e.g., "Python Fundamentals")
- **Description**: Add a brief description of what students will learn
- **Difficulty Level**: Choose from Beginner, Intermediate, or Advanced
- **Estimated Duration**: Select expected completion time

#### Step 2: Topic Selection
- **Browse Categories**: Explore pre-defined topic categories
- **Custom Topics**: Add your own topics using the "+" button
- **Topic Details**: Each topic can have specific learning objectives

#### Step 3: Module Configuration
- **Number of Modules**: Choose how many modules to generate (1-10)
- **Module Types**: 
  - 📚 **Fundamentals**: Core concepts and theory
  - 🛠️ **Implementation**: Hands-on coding exercises
  - 🎯 **Project**: Real-world application projects
  - 📝 **Assessment**: Tests and evaluations

#### Step 4: Advanced Options
- **Include Examples**: Toggle code examples in lessons
- **Add Exercises**: Include practice problems
- **Assessment Level**: Choose assessment complexity
- **Code Templates**: Include starter code files

### Generation Process

1. **Start Generation**: Click "Generate Lesson"
2. **Monitor Progress**: Real-time progress bar shows completion
3. **View Results**: Download or preview generated content
4. **Save Lesson**: Lessons are automatically saved to history

### Managing Generated Lessons

#### Lesson History
- **View All Lessons**: Browse previously generated lessons
- **Search & Filter**: Find lessons by name, date, or difficulty
- **Quick Actions**: Download, preview, or regenerate lessons

#### Lesson Preview
- **File Structure**: See all generated files and folders
- **Content Preview**: View lesson content before downloading
- **Module Overview**: Quick summary of each module

### Download Options
- **Complete Lesson**: ZIP file with all modules and resources
- **Individual Modules**: Download specific modules only
- **Source Code**: Get just the code files and exercises

## 💻 Command Line Interface (CLI)

### Installation
```bash
pip install lesson-generator
```

### Basic Usage

#### Generate a Simple Lesson
```bash
lesson-generator generate \
  --name "Python Basics" \
  --topic "variables,functions,loops" \
  --difficulty beginner \
  --modules 3
```

#### Advanced Generation
```bash
lesson-generator generate \
  --name "Advanced Python" \
  --description "Deep dive into Python advanced features" \
  --topic "decorators,metaclasses,async" \
  --difficulty advanced \
  --modules 5 \
  --include-projects \
  --output-dir ./my-lessons
```

### CLI Command Reference

#### `generate` - Create New Lesson
```bash
lesson-generator generate [OPTIONS]

Options:
  --name TEXT              Lesson name [required]
  --topic TEXT             Comma-separated topics [required]
  --difficulty CHOICE      beginner|intermediate|advanced
  --modules INTEGER        Number of modules (1-10)
  --description TEXT       Lesson description
  --include-examples      Include code examples
  --include-exercises     Include practice exercises
  --include-projects      Include project modules
  --output-dir PATH       Output directory
  --format CHOICE         html|markdown|pdf
```

#### `list` - View Generated Lessons
```bash
lesson-generator list [OPTIONS]

Options:
  --format CHOICE         table|json|simple
  --filter TEXT          Filter by name pattern
  --sort CHOICE          name|date|difficulty
```

#### `preview` - Preview Lesson Content
```bash
lesson-generator preview [LESSON_NAME] [OPTIONS]

Options:
  --module INTEGER       Preview specific module
  --format CHOICE        text|json|tree
```

#### `export` - Export Lesson
```bash
lesson-generator export [LESSON_NAME] [OPTIONS]

Options:
  --output PATH          Export location
  --format CHOICE        zip|tar|directory
  --include-source      Include source files
```

### Configuration File

Create `~/.lesson-generator/config.yaml`:

```yaml
# Default settings
defaults:
  difficulty: intermediate
  modules: 3
  include_examples: true
  include_exercises: true
  output_dir: ~/generated-lessons

# OpenAI settings
openai:
  api_key: ${OPENAI_API_KEY}
  model: gpt-4
  max_tokens: 4000

# Template settings
templates:
  default_language: python
  code_style: pep8
  comment_style: detailed

# Export settings
export:
  default_format: zip
  include_metadata: true
  compress_output: true
```

## 📝 Content Customization

### Template System

#### Custom Templates
Create custom lesson templates in `templates/`:

```python
# templates/my_exercise.py.j2
"""
{{ exercise_title }}
{{ "=" * exercise_title|length }}

{{ exercise_description }}

Requirements:
{% for req in requirements %}
- {{ req }}
{% endfor %}

Example:
```python
{{ example_code }}
```

Your solution:
"""

def {{ function_name }}():
    """
    {{ function_docstring }}
    """
    # TODO: Implement your solution here
    pass
```

#### Template Variables
- `{{ lesson_name }}`: Lesson title
- `{{ difficulty }}`: Difficulty level
- `{{ module_number }}`: Current module number
- `{{ topics }}`: List of topics covered
- `{{ examples }}`: Code examples
- `{{ exercises }}`: Practice exercises

### Topic Configuration

#### Custom Topics (`config/custom_topics.json`)
```json
{
  "web_development": {
    "name": "Web Development",
    "subtopics": [
      "HTML/CSS",
      "JavaScript",
      "React",
      "Node.js",
      "Databases"
    ],
    "prerequisites": ["programming_basics"],
    "learning_objectives": [
      "Build responsive web pages",
      "Create interactive user interfaces",
      "Develop full-stack applications"
    ]
  }
}
```

#### Topic Schema Validation
Topics must follow the schema in `config/topic_schema.json`:
- **name**: Display name for the topic
- **subtopics**: Array of related concepts
- **prerequisites**: Required prior knowledge
- **learning_objectives**: What students will achieve

## 🎯 Best Practices

### Lesson Design

#### 1. Progressive Difficulty
```
Module 1: Fundamentals (Theory + Simple examples)
Module 2: Implementation (Hands-on exercises)
Module 3: Integration (Combine concepts)
Module 4: Project (Real-world application)
Module 5: Assessment (Test understanding)
```

#### 2. Balanced Content
- **30% Theory**: Concepts and explanations
- **50% Practice**: Coding exercises and examples
- **20% Assessment**: Quizzes and projects

#### 3. Clear Learning Path
- Start with learning objectives
- Build concepts incrementally
- Include frequent checkpoints
- End with practical application

### Topic Selection

#### Effective Topics
✅ **Good**: "functions", "loops", "object-oriented-programming"
✅ **Good**: "web-apis", "database-design", "testing"

#### Topics to Avoid
❌ **Too Broad**: "programming", "computer-science"
❌ **Too Specific**: "python-list-comprehension-optimization"
❌ **Ambiguous**: "advanced-stuff", "miscellaneous"

### Module Planning

#### Recommended Module Types by Difficulty

**Beginner Lessons (1-3 modules)**
- Fundamentals only
- Simple examples
- Step-by-step exercises

**Intermediate Lessons (3-5 modules)**
- Fundamentals + Implementation
- Code examples + exercises
- Small projects

**Advanced Lessons (5-10 modules)**
- All module types
- Complex projects
- Performance considerations
- Real-world scenarios

## 🔧 Troubleshooting

### Common Issues

#### 1. Generation Fails
**Symptoms**: Error during lesson generation
**Solutions**:
- Check OpenAI API key validity
- Verify topic names are valid
- Reduce number of modules if timeout occurs
- Check internet connection

#### 2. Poor Quality Content
**Symptoms**: Generated content is generic or incorrect
**Solutions**:
- Use more specific topic names
- Add detailed descriptions
- Specify learning objectives
- Choose appropriate difficulty level

#### 3. Web Interface Not Loading
**Symptoms**: Browser shows error page
**Solutions**:
- Check if backend is running (`http://localhost:8000/api/docs`)
- Verify port 8000 is available
- Check browser console for JavaScript errors
- Try refreshing the page

#### 4. CLI Command Not Found
**Symptoms**: `lesson-generator: command not found`
**Solutions**:
```bash
# Reinstall package
pip install --upgrade lesson-generator

# Check installation
pip show lesson-generator

# Use python module
python -m lesson_generator generate --help
```

### Debug Mode

#### Enable Debug Logging
```bash
# CLI
lesson-generator --debug generate ...

# Web (in .env)
LOG_LEVEL=DEBUG
```

#### Check System Health
```bash
# Web interface
curl http://localhost:8000/api/v1/system/health

# CLI
lesson-generator status
```

## 📊 Usage Analytics

### Understanding Lesson Metrics

#### Generation Time
- **Simple lessons** (1-3 modules): 2-5 minutes
- **Complex lessons** (5+ modules): 10-20 minutes
- **Project-heavy lessons**: 15-30 minutes

#### Content Volume
- **Per module**: 1,000-2,000 words
- **Code examples**: 10-20 per module
- **Exercises**: 3-7 per module
- **Total files**: 5-15 per lesson

### Quality Indicators

#### Good Generation Signs
- ✅ Consistent terminology throughout
- ✅ Progressive difficulty increase
- ✅ Working code examples
- ✅ Clear exercise instructions
- ✅ Proper file organization

#### Review Required Signs
- ⚠️ Repetitive content across modules
- ⚠️ Missing code examples
- ⚠️ Unclear exercise requirements
- ⚠️ Inconsistent formatting

## 🎓 Educational Guidelines

### Lesson Structure

#### Recommended Flow
1. **Introduction**: What students will learn
2. **Prerequisites**: Required knowledge
3. **Core Concepts**: Theory and explanations
4. **Examples**: Practical demonstrations
5. **Exercises**: Hands-on practice
6. **Project**: Real-world application
7. **Assessment**: Knowledge verification
8. **Resources**: Further reading

### Assessment Design

#### Exercise Types
- **Fill-in-the-blank**: Complete code snippets
- **Debug exercises**: Fix broken code
- **Implementation**: Build from scratch
- **Extension**: Modify existing code
- **Research**: Explore related topics

#### Project Ideas by Domain
- **Web Development**: Build a todo app
- **Data Science**: Analyze a dataset
- **Machine Learning**: Train a simple model
- **Game Development**: Create a simple game
- **Mobile Apps**: Build a calculator

## 📞 Support & Resources

### Getting Help
- **Documentation**: See README.md for detailed setup
- **Issues**: Report bugs on GitHub
- **Discussions**: Join community discussions
- **Examples**: Check `reference_lesson/` for sample output

### Learning Resources
- **OpenAI API Documentation**: For understanding AI capabilities
- **Python Documentation**: For language-specific features
- **Educational Theory**: For effective lesson design
- **Template Guides**: For customization options

---

**🚀 Happy Teaching!**  
The Lesson Generator makes creating comprehensive programming lessons easy and efficient. Experiment with different topics and settings to find what works best for your students.