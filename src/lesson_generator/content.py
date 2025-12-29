"""
Content generation module.

This module handles AI-powered and fallback content generation for lessons.
It integrates with OpenAI's API to generate educational content and provides
fallback mechanisms when AI is not available.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import json

from .models import (
    GenerationConfig, 
    TopicConfig, 
    ModuleConfig,
    ContentGenerationRequest,
    ContentGenerationResponse
)

# Try to support both the modern OpenAI client and the older openai module
OPENAI_CLIENT_TYPE = None
OpenAI = None
openai_legacy = None
try:
    # Modern client (openai>=1.x)
    from openai import OpenAI as OpenAIClient  # type: ignore
    OPENAI_CLIENT_TYPE = "modern"
    OpenAI = OpenAIClient
except Exception:
    try:
        # Fallback to legacy openai package (pre-1.0 API)
        import openai as openai_legacy_module  # type: ignore
        OPENAI_CLIENT_TYPE = "legacy"
        openai_legacy = openai_legacy_module
    except Exception:
        OPENAI_CLIENT_TYPE = None


class ContentGenerator:
    """
    Handles content generation using AI or fallback methods.
    
    This class manages the generation of educational content including:
    - Learning paths and documentation
    - Code examples and exercises
    - Test cases and assignments
    - Explanatory text and descriptions
    """
    
    def __init__(self, config: GenerationConfig):
        """
        Initialize the content generator.
        
        Args:
            config: Generation configuration
        """
        self.config = config
        self.client = None
        self._content_cache = {}  # Cache for generated content
        self._generation_stats = {"ai_calls": 0, "cache_hits": 0, "fallback_calls": 0}
        
        # Initialize OpenAI client if configured and available
        if config.use_ai and config.openai_api_key and OPENAI_CLIENT_TYPE:
            try:
                if OPENAI_CLIENT_TYPE == "modern":
                    # Modern client: create instance with provided API key
                    self.client = OpenAI(
                        api_key=config.openai_api_key,
                        organization=config.openai_organization
                    )
                else:
                    # Legacy client: set global api_key on module
                    openai_legacy.api_key = config.openai_api_key
                    if getattr(config, 'openai_organization', None):
                        try:
                            openai_legacy.organization = config.openai_organization
                        except Exception:
                            # older lib may not support organization attribute
                            pass
                    self.client = openai_legacy

                self.ai_enabled = True
                if config.verbose:
                    print(f"✓ OpenAI client initialized (client_type={OPENAI_CLIENT_TYPE}) with model: {config.openai_model}")
            except Exception as e:
                if config.verbose:
                    print(f"⚠ OpenAI initialization failed: {e}")
                self.ai_enabled = False
        else:
            self.ai_enabled = False
            if config.verbose and config.use_ai:
                reasons = []
                if not config.openai_api_key:
                    reasons.append("no API key")
                if not OPENAI_CLIENT_TYPE:
                    reasons.append("OpenAI package not available")
                print(f"⚠ AI disabled: {', '.join(reasons)}")
    
    @staticmethod
    def _create_safe_class_name(topic_name: str, suffix: str = "Assignment") -> str:
        """
        Create a valid Python class name from a topic name.
        
        Args:
            topic_name: Original topic name (may contain hyphens, spaces, etc.)
            suffix: Suffix to append to the class name
            
        Returns:
            Valid Python class identifier
        """
        # Create valid Python class name by removing hyphens, spaces, and other invalid characters
        safe_name = ''.join(c.title() if c.isalnum() else '' for c in topic_name)
        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = 'Lesson' + safe_name
        if not safe_name or not safe_name.isidentifier():
            safe_name = 'Assignment'
        return f"{safe_name}{suffix}"
    
    def generate_content(
        self, 
        content_type: str, 
        topic: TopicConfig, 
        module_config: Optional[Any] = None,
        extra_context: Optional[dict] = None
    ) -> ContentGenerationResponse:
        """
        Generate content based on the specified type and context.
        
        Args:
            content_type: Type of content to generate
            topic: Topic configuration
            module_config: Optional module configuration
            extra_context: Optional extra context like code to test
            
        Returns:
            Generated content response
        """
        start_time = time.time()
        
        # Create cache key for cost optimization
        cache_key = self._create_cache_key(content_type, topic, module_config)
        
        # Check cache first to avoid duplicate API calls
        if self.config.enable_cache and cache_key in self._content_cache:
            self._generation_stats["cache_hits"] += 1
            cached_response = self._content_cache[cache_key]
            if self.config.verbose:
                print(f"    📋 Using cached content for {content_type}")
            return cached_response
        
        # Create generation request
        if module_config is None:
            # Create a default module config for content that doesn't need specific module context
            from .models import ModuleConfig, ModuleType, CodeComplexity
            module_config = ModuleConfig(
                name=f"{topic.name} Module",
                type=ModuleType.STARTER,
                focus_areas=["general"],
                code_complexity=CodeComplexity.SIMPLE
            )
        
        request = ContentGenerationRequest(
            topic=topic,
            module=module_config,
            content_type=content_type,
            additional_context=extra_context or {}
        )
        
        # Generate content using AI or fallback
        if self.config.verbose:
            print(f"🤖 Content generation decision for '{content_type}':")
            print(f"   - OpenAI client: {bool(self.client)}")
            print(f"   - use_ai config: {self.config.use_ai}")
            print(f"   - ai_enabled: {getattr(self, 'ai_enabled', 'NOT_SET')}")
            print(f"   - API key available: {bool(self.config.openai_api_key)}")
            print(f"   - OpenAI package present: {bool(OPENAI_CLIENT_TYPE)} (type={OPENAI_CLIENT_TYPE})")
            
        if self.client and self.config.use_ai and getattr(self, 'ai_enabled', False):
            if self.config.verbose:
                print(f"🚀 Using AI to generate {content_type}")
            response = self._generate_ai_content(request, start_time)
            self._generation_stats["ai_calls"] += 1
        else:
            if self.config.verbose:
                reasons = []
                if not self.client:
                    reasons.append("no OpenAI client")
                if not self.config.use_ai:
                    reasons.append("AI disabled in config")
                if not getattr(self, 'ai_enabled', False):
                    reasons.append("AI not enabled")
                print(f"⚠️ Using fallback for {content_type} - Reasons: {', '.join(reasons)}")
            response = self._generate_fallback_content(request, start_time)
            self._generation_stats["fallback_calls"] += 1
        
        # Cache the response for future use
        if self.config.enable_cache:
            self._content_cache[cache_key] = response
        
        return response
    
    def _generate_ai_content(
        self, 
        request: ContentGenerationRequest, 
        start_time: float
    ) -> ContentGenerationResponse:
        """Generate content using OpenAI API."""
        
        if self.config.verbose:
            print(f"🔥 Making OpenAI API call for {request.content_type}")
        
        # Create appropriate prompt based on content type
        prompt = self._create_prompt(request)
        
        try:
            # Add rate limiting delay
            time.sleep(self.config.rate_limit_delay)
            
            if self.config.verbose:
                print(f"📡 Calling OpenAI API with model: {self._get_cost_optimal_model()} (client_type={OPENAI_CLIENT_TYPE})")

            # Prepare messages
            messages = [
                {"role": "system", "content": self._get_system_prompt(request.content_type)},
                {"role": "user", "content": self._optimize_prompt_for_cost(prompt, request.content_type)}
            ]

            if OPENAI_CLIENT_TYPE == "modern":
                response = self.client.chat.completions.create(
                    model=self._get_cost_optimal_model(),
                    messages=messages,
                    temperature=0.3,
                    max_tokens=self._get_optimal_max_tokens(request.content_type),
                )

                # Modern client response shape
                content = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if getattr(response, 'usage', None) else 0

            elif OPENAI_CLIENT_TYPE == "legacy":
                # Legacy client: use openai.ChatCompletion.create
                response = self.client.ChatCompletion.create(
                    model=self._get_cost_optimal_model(),
                    messages=messages,
                    temperature=0.3,
                    max_tokens=self._get_optimal_max_tokens(request.content_type),
                )

                # Legacy response: dict-like
                choice = response.choices[0]
                # Some older versions have .message or ['message'] with dict
                if hasattr(choice, 'message') and hasattr(choice.message, 'get'):
                    content = choice.message.get('content', '').strip()
                else:
                    # Fallback to indexing into dict
                    try:
                        content = choice['message']['content'].strip()
                    except Exception:
                        # Another fallback: text field
                        content = getattr(choice, 'text', '') or choice.get('text', '')
                        content = content.strip() if content else content

                # Legacy usage may or may not provide usage info
                try:
                    tokens_used = response['usage']['total_tokens'] if isinstance(response, dict) and 'usage' in response else getattr(response, 'usage', {}).get('total_tokens', 0)
                except Exception:
                    tokens_used = 0

            else:
                raise RuntimeError("No OpenAI client available")

            # Extract code from markdown blocks if it's Python content
            if request.content_type in ["starter_example", "assignment_a", "assignment_b", "test_starter", "test_assignment_a", "test_assignment_b"]:
                content = self._extract_code_from_markdown(content)

            return ContentGenerationResponse(
                content=content,
                model_used=self.config.openai_model,
                tokens_used=tokens_used,
                generation_time_seconds=time.time() - start_time,
                success=True
            )
            
        except Exception as e:
            if self.config.verbose:
                print(f"⚠ AI generation failed: {e}, using fallback")
            return self._generate_fallback_content(request, start_time)
    
    def _get_cost_optimal_model(self) -> str:
        """Get the most cost-effective model for the task."""
        # Use GPT-3.5-turbo instead of GPT-4 for significant cost savings
        # Only use GPT-4 for complex content types that really need it
        complex_types = ["learning_path", "project_assignment"]
        
        if self.config.openai_model == "gpt-4" and hasattr(self, '_current_content_type'):
            if self._current_content_type not in complex_types:
                return "gpt-3.5-turbo"
        
        return self.config.openai_model
    
    def _get_optimal_max_tokens(self, content_type: str) -> int:
        """Get optimal token limits based on content type to minimize costs."""
        token_limits = {
            "starter_example": 800,      # Reduced from 2000
            "assignment_a": 600,         # Reduced from 2000
            "assignment_b": 600,         # Reduced from 2000
            "test_starter": 400,         # Reduced from 2000
            "test_assignment_a": 400,    # Reduced from 2000
            "test_assignment_b": 400,    # Reduced from 2000
            "extra_exercises": 800,      # Reduced from 2000
            "learning_path": 1200,       # Keep higher for quality
        }
        
        return token_limits.get(content_type, 600)  # Conservative default
    
    def _optimize_prompt_for_cost(self, prompt: str, content_type: str) -> str:
        """Optimize prompts to reduce token usage while maintaining quality."""
        # Store content type for model selection
        self._current_content_type = content_type
        
        # Add cost-optimization instructions
        optimizations = {
            "starter_example": "Generate a concise code example with minimal comments. Focus on core functionality only.",
            "assignment_a": "Create a brief assignment with clear objectives. Keep instructions concise.",
            "assignment_b": "Generate a short, focused assignment. Avoid lengthy descriptions.",
            "test_starter": "Write minimal test cases covering key functionality only.",
            "test_assignment_a": "Create essential test cases. Keep test names descriptive but brief.",
            "test_assignment_b": "Generate focused test cases. Prioritize coverage over quantity.",
            "extra_exercises": "List 3-5 concise exercises. Keep descriptions short and actionable.",
            "learning_path": "Create a structured learning guide. Be comprehensive but concise."
        }
        
        optimization_prefix = optimizations.get(content_type, "Generate concise, focused content.")
        return f"{optimization_prefix}\n\n{prompt}"
    
    def _create_cache_key(self, content_type: str, topic: TopicConfig, module_config) -> str:
        """Create a cache key for content to avoid duplicate generation."""
        module_name = module_config.name if module_config else "no_module"
        module_type = module_config.type if module_config else "no_type"
        
        # Create a simple hash of the key components
        key_components = [
            content_type,
            topic.name.lower().replace(" ", "_"),
            str(topic.difficulty),
            module_name.lower().replace(" ", "_"),
            str(module_type)
        ]
        
        return "|".join(key_components)
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about content generation for cost analysis."""
        total_calls = sum(self._generation_stats.values())
        
        stats = self._generation_stats.copy()
        stats["total_calls"] = total_calls
        stats["cache_efficiency"] = (
            self._generation_stats["cache_hits"] / max(total_calls, 1)
        ) * 100
        stats["ai_usage"] = (
            self._generation_stats["ai_calls"] / max(total_calls, 1)
        ) * 100
        
        return stats
    
    def print_cost_summary(self):
        """Print a cost optimization summary."""
        if not self.config.verbose:
            return
            
        stats = self.get_generation_stats()
        print(f"\n💰 Cost Optimization Summary:")
        print(f"  AI Calls: {stats['ai_calls']}")
        print(f"  Cache Hits: {stats['cache_hits']}")
        print(f"  Fallback Calls: {stats['fallback_calls']}")
        print(f"  Cache Efficiency: {stats['cache_efficiency']:.1f}%")
        print(f"  AI Usage: {stats['ai_usage']:.1f}%")
    
    def _generate_fallback_content(
        self, 
        request: ContentGenerationRequest, 
        start_time: float
    ) -> ContentGenerationResponse:
        """Generate fallback content when AI is unavailable."""
        
        content_generators = {
            "learning_path": self._generate_learning_path_fallback,
            "starter_example": self._generate_starter_example_fallback,
            "assignment_a": self._generate_assignment_a_fallback,
            "assignment_b": self._generate_assignment_b_fallback,
            "test_starter": self._generate_test_fallback,
            "test_assignment_a": self._generate_test_assignment_a_fallback,
            "test_assignment_b": self._generate_test_assignment_b_fallback,
            "extra_exercises": self._generate_extra_exercises_fallback
        }
        
        generator = content_generators.get(request.content_type, self._generate_generic_fallback)
        content = generator(request)
        
        return ContentGenerationResponse(
            content=content,
            model_used="fallback",
            generation_time_seconds=time.time() - start_time,
            success=True
        )
    
    def _create_prompt(self, request: ContentGenerationRequest) -> str:
        """Create appropriate prompt for OpenAI based on content type."""
        
        base_context = f"""
Topic: {request.topic.name}
Difficulty: {request.topic.difficulty}
Module: {request.module.name}
Module Type: {request.module.type}
Focus Areas: {', '.join(request.module.focus_areas)}
Learning Objectives: {', '.join(request.topic.learning_objectives)}
"""
        
        prompts = {
            "learning_path": f"""
Create a comprehensive learning path guide for {request.module.name}.
{base_context}

Generate a detailed markdown guide with COMPLETE content including:

## 🎯 Learning Objectives
List 4-5 specific, measurable learning objectives for {', '.join(request.module.focus_areas)} in {request.topic.name}

## 📚 Introduction  
2-3 paragraph introduction explaining what {request.topic.name} is and why it's important

## 🔑 Key Concepts
Detailed explanation of 3-4 key concepts students will learn:
- Concept 1: Definition and examples
- Concept 2: Definition and examples  
- Concept 3: Definition and examples

Include practical examples relevant to {request.topic.name} for {request.topic.difficulty} level students.

## 🛠️ Step-by-Step Learning Path

Follow this exact sequence for optimal learning:

### 📝 **Step 1: Study the Starter Example**
**File to work with**: `starter_example.py`

**ACTION ITEMS**:
1. **Open and read** `starter_example.py` carefully
2. **Run the code** to see the concepts in action:
   ```bash
   python starter_example.py
   ```
3. **Understand the implementation** - examine how each method demonstrates {', '.join(request.module.focus_areas)} concepts
4. **Review the comments** and docstrings to understand the design decisions

### 🧪 **Step 2: Understand the Tests**
**File to work with**: `test_starter_example.py`

**ACTION ITEMS**:
1. **Read through** `test_starter_example.py` to understand testing approaches
2. **Run the tests** to see how the starter example is validated:
   ```bash
   python -m pytest test_starter_example.py -v
   ```
3. **Analyze test patterns** - notice how different scenarios are tested
4. **Understand test structure** - observe setup, execution, and assertion patterns

### 📝 **Step 3: Write Tests for Assignment A**
**Files to work with**: `assignment_a.py` → `test_assignment_a.py`

**OBJECTIVE**: Practice test-driven learning by writing comprehensive tests

**ACTION ITEMS**:
1. **Study the code** in `assignment_a.py` thoroughly
2. **Analyze the class structure** and method signatures
3. **Write comprehensive tests** in `test_assignment_a.py` to achieve 100% coverage
4. **Test edge cases** and error conditions
5. **Run your tests** to verify they work:
   ```bash
   python -m pytest test_assignment_a.py -v
   ```

### 🚀 **Step 4: Implement Assignment B**
**Files to work with**: `test_assignment_b.py` → `assignment_b.py`

**OBJECTIVE**: Practice implementation by making tests pass

**ACTION ITEMS**:
1. **Study the test requirements** in `test_assignment_b.py`
2. **Understand what needs to be implemented** by reading test expectations
3. **Implement the methods** in `assignment_b.py` to make tests pass
4. **Run tests iteratively** to check progress:
   ```bash
   python -m pytest test_assignment_b.py -v
   ```
5. **Refine your implementation** until all tests pass

### 🎯 **Step 5: Extra Practice**
**File to work with**: `extra_exercises.md`

**ACTION ITEMS**:
1. **Complete the additional exercises** for deeper understanding
2. **Apply concepts** to new scenarios
3. **Challenge yourself** with advanced variations

## ✅ Success Criteria & Estimated Time
- [ ] Successfully ran and understood `starter_example.py`
- [ ] Comprehended test patterns in `test_starter_example.py`
- [ ] Achieved 100% test coverage for `assignment_a.py`
- [ ] Made all tests pass in `test_assignment_b.py`
- [ ] Completed extra exercises

**Estimated Time**: {60 if request.topic.difficulty == 'beginner' else 90 if request.topic.difficulty == 'intermediate' else 120} minutes

Make it engaging and practical with real examples, not placeholders.
""",
            
            "starter_example": f"""
Create a Python code example for this module.
{base_context}

Generate ONLY executable Python code (no markdown formatting) with:
1. A complete Python class demonstrating {', '.join(request.module.focus_areas)}
2. Clear docstrings explaining the purpose
3. Well-commented methods with practical examples
4. Appropriate complexity for {request.topic.difficulty} level
5. Error handling where relevant
6. Example usage at the end

Return only valid Python code that can be executed directly.
""",
            
            "assignment_a": f"""
Create Python code that students will write tests for.
{base_context}

Generate ONLY executable Python code (no markdown formatting) with:
1. A Python class demonstrating {', '.join(request.module.focus_areas)}
2. Multiple methods of varying complexity for {request.topic.difficulty} level
3. Clear docstrings with parameters and return values
4. Some edge cases and error conditions to test
5. Methods that require comprehensive testing

Return only valid Python code that students can write tests for.
""",
            
            "assignment_b": f"""
Create a Python class template with method signatures and docstrings.
{base_context}

Generate ONLY executable Python code (no markdown formatting) with:
1. A Python class focused on {', '.join(request.module.focus_areas)}
2. Method signatures only with 'pass' or 'raise NotImplementedError()'
3. Detailed docstrings explaining what each method should do
4. Parameter descriptions and return value specifications
5. Appropriate complexity for {request.topic.difficulty} level

Students will implement these methods to make tests pass.
Return only valid Python code template.
""",
            
            "extra_exercises": f"""
Create 3 specific practice exercises for {request.module.name} focusing on {', '.join(request.module.focus_areas)}.
{base_context}

Generate a markdown document with COMPLETE, SPECIFIC exercises:

## Exercise 1: Basic {request.topic.name.title()} Practice
**Difficulty**: Beginner  
Create a specific coding challenge that practices {request.module.focus_areas[0] if request.module.focus_areas else request.topic.name}.
Include:
- Exact problem description with specific requirements
- Example input/output 
- Step-by-step solution approach
- Code template to get started

## Exercise 2: Intermediate Challenge  
**Difficulty**: Intermediate
Design a more complex problem involving {', '.join(request.module.focus_areas[:2]) if len(request.module.focus_areas) > 1 else request.topic.name}.
Include specific requirements, constraints, and expected behavior.

## Exercise 3: Real-World Application
**Difficulty**: Advanced
Create a practical project that applies {request.topic.name} to solve a real problem.
Provide specific requirements and deliverables.

NO placeholders - provide complete, actionable exercises.
""",
            
            "test_starter": f"""
Create comprehensive pytest test cases for the starter example.
{base_context}

{f"CODE TO TEST:{chr(10)}{request.additional_context.get('code_to_test', 'No code provided')}{chr(10)}" if request.additional_context.get('code_to_test') else ""}

Generate ONLY executable Python test code (no markdown formatting) with:
1. Import statements: `import pytest` and `from starter_example import ClassName` (use the actual class name from the code above)
2. Test class that follows pytest conventions
3. Comprehensive test methods covering:
   - Normal functionality  
   - Edge cases
   - Error conditions
   - Method interactions
4. Use clear, descriptive test method names
5. Include docstrings explaining what each test verifies
6. Use appropriate pytest features (fixtures, parametrize, etc.)

CRITICAL SYNTAX REQUIREMENTS:
- ALL strings must be properly quoted with matching quotes
- ALL parentheses, brackets, and braces must be balanced
- ALL indentation must use 4 spaces consistently
- Import from the filename 'starter_example', not from any module name
- Example: `from starter_example import ActualClassName`

Analyze the actual code structure and create tests that match the real class names and methods.
Return only valid, syntax-error-free Python test code.
""",
            
            "test_assignment_a": f"""
Create comprehensive pytest test cases for assignment A.
{base_context}

{f"CODE TO TEST:{chr(10)}{request.additional_context.get('code_to_test', 'No code provided')}{chr(10)}" if request.additional_context.get('code_to_test') else ""}

Generate ONLY executable Python test code (no markdown formatting) with:
1. Import statements: `import pytest` and `from assignment_a import ClassName` (use the actual class name from the code above)
2. Test class following pytest conventions  
3. Comprehensive test methods that achieve high coverage:
   - All public methods tested
   - Normal cases and edge cases
   - Error conditions and exception handling
   - Boundary conditions
4. Use descriptive test method names
5. Include setup and teardown if needed
6. Use pytest features appropriately

CRITICAL SYNTAX REQUIREMENTS:
- ALL strings must be properly quoted with matching quotes
- ALL parentheses, brackets, and braces must be balanced
- ALL indentation must use 4 spaces consistently
- Import from the filename 'assignment_a', not from any module name
- Example: `from assignment_a import ActualClassName`

Analyze the actual code structure and create tests that match the real class names and methods.
Return only valid, syntax-error-free Python test code that students can run to verify their understanding.
""",
            
            "test_assignment_b": f"""
Create pytest test cases that assignment B code must pass.
{base_context}

{f"CODE TO TEST:{chr(10)}{request.additional_context.get('code_to_test', 'No code provided')}{chr(10)}" if request.additional_context.get('code_to_test') else ""}

Generate ONLY executable Python test code (no markdown formatting) with:
1. Import statements: `import pytest` and `from assignment_b import ClassName` (use the actual class name from the code above)
2. Test class following pytest conventions
3. Test methods that verify the implementation requirements:
   - Test method signatures and return types
   - Test expected behavior and outputs
   - Test edge cases and error handling
   - Test method interactions
4. Use clear, descriptive test names
5. Include helpful assertions with descriptive messages

CRITICAL SYNTAX REQUIREMENTS:
- ALL strings must be properly quoted with matching quotes
- ALL parentheses, brackets, and braces must be balanced
- ALL indentation must use 4 spaces consistently
- Import from the filename 'assignment_b', not from any module name
- Example: `from assignment_b import ActualClassName`

Analyze the actual code structure and create tests that the student implementation must pass.
Return only valid, syntax-error-free Python test code.
"""
        }
        
        return prompts.get(request.content_type, f"Generate {request.content_type} content for {request.module.name}")
    
    def _generate_learning_path_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback learning path content."""
        return f"""# {request.module.name} - Learning Path

## 🎯 Learning Objectives

By the end of this module, you will understand:
{chr(10).join(f"- {objective}" for objective in request.topic.learning_objectives)}

## 🔑 Key Concepts

{chr(10).join(f"- **{area.title()}**: Core concept in {request.topic.name.lower()}" for area in request.module.focus_areas)}

## �️ Step-by-Step Learning Path

Follow this exact sequence for optimal learning:

### 📝 **Step 1: Study the Starter Example**
**File to work with**: `starter_example.py`

**ACTION ITEMS**:
1. **Open and read** `starter_example.py` carefully
2. **Run the code** to see the concepts in action:
   ```bash
   python starter_example.py
   ```
3. **Understand the implementation** - examine how each method demonstrates {", ".join(request.module.focus_areas)} concepts
4. **Review the comments** and docstrings to understand the design decisions

### 🧪 **Step 2: Understand the Tests**
**File to work with**: `test_starter_example.py`

**ACTION ITEMS**:
1. **Read through** `test_starter_example.py` to understand testing approaches
2. **Run the tests** to see how the starter example is validated:
   ```bash
   python -m pytest test_starter_example.py -v
   ```
3. **Analyze test patterns** - notice how different scenarios are tested
4. **Understand test structure** - observe setup, execution, and assertion patterns

### 📝 **Step 3: Write Tests for Assignment A**
**Files to work with**: `assignment_a.py` → `test_assignment_a.py`

**OBJECTIVE**: Practice test-driven learning by writing comprehensive tests

**ACTION ITEMS**:
1. **Study the code** in `assignment_a.py` thoroughly
2. **Analyze the class structure** and method signatures
3. **Write comprehensive tests** in `test_assignment_a.py` to achieve 100% coverage
4. **Test edge cases** and error conditions
5. **Run your tests** to verify they work:
   ```bash
   python -m pytest test_assignment_a.py -v
   ```

### 🚀 **Step 4: Implement Assignment B**
**Files to work with**: `test_assignment_b.py` → `assignment_b.py`

**OBJECTIVE**: Practice implementation by making tests pass

**ACTION ITEMS**:
1. **Study the test requirements** in `test_assignment_b.py`
2. **Understand what needs to be implemented** by reading test expectations
3. **Implement the methods** in `assignment_b.py` to make tests pass
4. **Run tests iteratively** to check progress:
   ```bash
   python -m pytest test_assignment_b.py -v
   ```
5. **Refine your implementation** until all tests pass

### 🎯 **Step 5: Extra Practice**
**File to work with**: `extra_exercises.md`

**ACTION ITEMS**:
1. **Complete the additional exercises** for deeper understanding
2. **Apply concepts** to new scenarios
3. **Challenge yourself** with advanced variations

## ✅ Success Criteria

- [ ] Successfully ran and understood `starter_example.py`
- [ ] Comprehended test patterns in `test_starter_example.py`
- [ ] Achieved 100% test coverage for `assignment_a.py`
- [ ] Made all tests pass in `test_assignment_b.py`
- [ ] Completed extra exercises

**Estimated Time**: {60 if request.topic.difficulty == 'beginner' else 90 if request.topic.difficulty == 'intermediate' else 120} minutes
"""
    
    def _generate_starter_example_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback starter example."""
        class_name = self._create_safe_class_name(request.topic.name, "Example")
        return f'''"""
Starter Example: {request.module.name}

This example demonstrates {", ".join(request.module.focus_areas)} concepts
in {request.topic.name.lower()}.

Learning Objectives:
- Understand {request.topic.name.lower()} concepts
- Practice implementation and testing skills
"""

# Starter Example for {request.module.name}

class {class_name}:
    """
    Example class for {request.module.name}.
    
    This is a starter example to demonstrate {", ".join(request.module.focus_areas)} concepts
    in {request.topic.name.lower()}.
    Study this code to understand the patterns and techniques used.
    """
    
    def __init__(self):
        """Initialize the example."""
        self.data = {{}}
    
    def example_method(self, param):
        """
        Example method demonstrating basic functionality.
        
        Args:
            param: Example parameter
            
        Returns:
            Processed result
        """
        # TODO: Add meaningful implementation
        return f"Processed: {{param}}"
    
    def demonstrate_concept(self):
        """Demonstrate the main concept of this module."""
        # TODO: Add concept demonstration
        print(f"Demonstrating {request.module.focus_areas[0] if request.module.focus_areas else 'concepts'}")


if __name__ == "__main__":
    example = {class_name}()
    result = example.example_method("test")
    print(result)
    example.demonstrate_concept()
'''
    
    def _generate_assignment_a_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback assignment A."""
        class_name = self._create_safe_class_name(request.topic.name, "Assignment")
        return f'''"""
Assignment A: {request.module.name}
Students need to write tests to achieve 100% coverage.

Learning Objectives:
- Understand {request.topic.name.lower()} concepts
- Practice implementation and testing skills
"""

# Assignment A: {request.module.name}
# Students need to write tests for this code

class {class_name}:
    """
    Assignment class for testing practice.
    
    TASK: Write comprehensive tests for this class in test_assignment_a.py
    Focus on:
    - Testing all methods with various inputs
    - Edge cases and error conditions
    - Code coverage of all branches
    """
    
    def process_data(self, data):
        """Process input data and return result."""
        if not data:
            return None
        return str(data).upper()
    
    def calculate_result(self, a, b):
        """Calculate result from two inputs."""
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise TypeError("Inputs must be numbers")
        return a + b
    
    def validate_input(self, value):
        """Validate input and return boolean."""
        return value is not None and len(str(value)) > 0
'''
    
    def _generate_assignment_b_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback assignment B."""
        class_name = self._create_safe_class_name(request.topic.name, "Implementation")
        return f'''"""
Assignment B: {request.module.name}
Students need to implement methods to make tests pass.

Learning Objectives:
- Understand {request.topic.name.lower()} concepts
- Practice implementation and testing skills
"""

# Assignment B: {request.module.name}  
# Students need to implement code to make tests pass

class {class_name}:
    """
    Implementation class for {request.module.name}.
    
    TASK: Implement the methods below to make the tests in test_assignment_b.py pass.
    Follow the method signatures and docstrings carefully.
    """
    
    def __init__(self):
        """Initialize the implementation."""
        # TODO: Add initialization code
        pass
    
    def required_method(self, param):
        """
        Implement this method according to test requirements.
        
        Args:
            param: Input parameter
            
        Returns:
            Expected result based on tests
        """
        # TODO: Implement to make tests pass
        raise NotImplementedError("Implement this method")
    
    def helper_method(self, data):
        """
        Helper method for processing data.
        
        Args:
            data: Data to process
            
        Returns:
            Processed data
        """
        # TODO: Implement helper functionality
        raise NotImplementedError("Implement this method")
'''
    
    def _generate_test_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback test content."""
        return f'''"""
Tests for {request.module.name}
"""

import pytest


class TestModule:
    """Test cases for the module."""
    
    def setup_method(self):
        """Set up test fixtures."""
        pass
    
    def test_basic_functionality(self):
        """Test basic functionality works."""
        # TODO: Add meaningful test
        assert True
    
    def test_edge_cases(self):
        """Test edge cases."""
        # TODO: Add edge case tests
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
    
    def _generate_test_assignment_a_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback assignment A tests."""
        return f'''"""
Assignment A Test Template: {request.module.name}

STUDENT TASK: Write comprehensive tests for assignment_a.py
Focus on achieving 100% code coverage and testing edge cases.
"""

import pytest
# TODO: Import your classes from assignment_a.py


class TestAssignment:
    """
    Test cases for Assignment A.
    
    INSTRUCTIONS:
    1. Import the class from assignment_a.py
    2. Write tests for all methods
    3. Achieve 100% code coverage
    4. Test edge cases and error conditions
    """
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # TODO: Initialize test objects here
        pass
    
    # TODO: Write your test methods here
    def test_placeholder(self):
        """Remove this test once you add real tests."""
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
    
    def _generate_test_assignment_b_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback assignment B tests."""
        class_name = f"{request.module.name.replace(' ', '')}Implementation"
        return f'''"""
Assignment B Tests: {request.module.name}
Students need to implement code to make these tests pass.
"""

import pytest
from assignment_b import {class_name}


class Test{class_name}:
    """Tests that student implementation must pass."""
    
    def setup_method(self):
        """Setup test fixture."""
        self.implementation = {class_name}()
    
    def test_required_method_basic(self):
        """Test required method with basic input."""
        result = self.implementation.required_method("test")
        assert result is not None
    
    def test_helper_method(self):
        """Test helper method functionality."""
        result = self.implementation.helper_method("data")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
    
    def _generate_extra_exercises_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate fallback extra exercises."""
        return f"""# Extra Exercises: {request.module.name}

## 🎯 Objective
Practice and reinforce {', '.join(request.module.focus_areas)} concepts.

## 📚 Focus Areas
{chr(10).join(f"- {area.title()}" for area in request.module.focus_areas)}

---

## 🚀 Exercise 1: Basic Practice
**Difficulty**: ⭐⭐

Apply the concepts from this module in a simple scenario.

**Task**:
1. Create a simple implementation using the module concepts
2. Write tests for your implementation
3. Ensure all tests pass

---

## 🚀 Exercise 2: Intermediate Challenge
**Difficulty**: ⭐⭐⭐

Extend the concepts to handle more complex scenarios.

**Task**:
1. Design a solution that combines multiple concepts
2. Handle edge cases and errors
3. Write comprehensive tests

---

## 🚀 Exercise 3: Advanced Application
**Difficulty**: ⭐⭐⭐⭐

Create a real-world application using the module concepts.

**Task**:
1. Identify a practical problem to solve
2. Design and implement a complete solution
3. Include documentation and tests
4. Consider performance and maintainability

## 🧪 Testing Your Solutions

Run your exercise tests:
```bash
pytest test_exercise_*.py -v
```

## 📋 Success Criteria

- [ ] Complete all exercises
- [ ] Achieve good test coverage
- [ ] Follow best practices
- [ ] Document your solutions
"""
    
    def _get_system_prompt(self, content_type: str) -> str:
        """Get appropriate system prompt based on content type."""
        if content_type in ["test_starter", "test_assignment_a", "test_assignment_b"]:
            return """You are an expert Python programming instructor specializing in test generation. 

CRITICAL REQUIREMENTS:
1. Generate ONLY valid, executable Python code with NO syntax errors
2. ALL strings must be properly quoted and terminated
3. ALL parentheses, brackets, and braces must be balanced
4. ALL indentation must be consistent (4 spaces)
5. NO markdown formatting, comments outside the code, or explanations
6. Verify all imports are correct and match actual file names
7. Double-check all method names match the actual code being tested

Focus on creating comprehensive, syntactically perfect pytest test cases."""
        elif content_type in ["starter_example", "assignment_a", "assignment_b"]:
            return """You are an expert Python programming instructor. 

CRITICAL REQUIREMENTS:
1. Generate ONLY valid, executable Python code with NO syntax errors
2. ALL strings must be properly quoted and terminated  
3. ALL parentheses, brackets, and braces must be balanced
4. ALL indentation must be consistent (4 spaces)
5. NO markdown formatting, comments outside the code, or explanations
6. Include proper docstrings and meaningful implementations
7. Focus on practical, educational examples with proper error handling

Generate clean, professional Python code that students can learn from."""
        else:
            return "You are an expert educational content creator. Generate practical, engaging educational content focused on programming concepts. Use clear explanations and real-world examples."

    def _extract_code_from_markdown(self, content: str) -> str:
        """Extract Python code from markdown code blocks."""
        import re
        
        # Look for Python code blocks (```python or ```py or just ```)
        code_block_pattern = r'```(?:python|py)?\n?(.*?)```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        if matches:
            # If we found code blocks, return the first/largest one
            largest_block = max(matches, key=len)
            return largest_block.strip()
        
        # If no code blocks found, return original content
        return content

    def _generate_generic_fallback(self, request: ContentGenerationRequest) -> str:
        """Generate generic fallback content."""
        return f"""# {request.content_type.title()}: {request.module.name}

This is placeholder content for {request.content_type}.

## Module Information
- **Topic**: {request.topic.name}
- **Module**: {request.module.name}
- **Type**: {request.module.type}
- **Focus Areas**: {', '.join(request.module.focus_areas)}
- **Difficulty**: {request.topic.difficulty}

## TODO
Implement {request.content_type} content for this module.
"""