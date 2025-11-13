# StoryForge AI Testing Guide

This document provides comprehensive information about testing the StoryForge AI Interactive Story Engine.

## 🎯 Overview

StoryForge AI has been successfully rebranded from a licensed property simulator to a generic sci-fi story generation platform. Our testing strategy ensures:

- ✅ Complete removal of branded content
- ✅ Generic sci-fi theme consistency  
- ✅ High-quality story generation
- ✅ Robust API functionality
- ✅ Reliable character system

## 📊 Test Organization

### Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| **API Tests** | `tests/test_api_endpoints_comprehensive.py` | Complete API endpoint validation |
| **Character Tests** | `tests/test_character_system_comprehensive.py` | Character loading & validation |
| **Story Tests** | `tests/test_story_generation_comprehensive.py` | Narrative generation & quality |
| **Integration Tests** | `tests/test_integration_comprehensive.py` | End-to-end system workflows |
| **Frontend Tests** | `tests/test_frontend_comprehensive.js` | React UI components & interactions |
| **Legacy Tests** | `test_*.py` (root level) | Original component tests |

### Test Markers

Use pytest markers to run specific test categories:

```bash
# Run all API tests
pytest -m api

# Run integration tests
pytest -m integration

# Run story generation tests  
pytest -m story

# Run performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

## 🚀 Running Tests

### Backend Tests (Python)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_api_endpoints_comprehensive.py

# Run with verbose output
pytest -v

# Run specific test category
pytest -m "api and not slow"

# Generate coverage report
pytest --cov=. --cov-report=term-missing --cov-report=html:htmlcov
```

### Frontend Tests (JavaScript)

```bash
# Navigate to frontend directory
cd frontend

# Run all frontend tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- tests/test_frontend_comprehensive.js
```

### Integration Testing

```bash
# Start API + frontend via daemon (non-blocking)
npm run dev:daemon

# Run integration tests
pytest tests/test_integration_comprehensive.py -v

# Stop background services when finished
npm run dev:stop
```

## 🎨 Generic Sci-Fi Content Validation

### Key Validation Points

All tests validate that the system produces **generic sci-fi content** instead of branded material:

**✅ Approved Generic Content:**
- "Galactic Defense Forces" 
- "Scientific Research Institute"
- "Galactic Engineering Corps"
- "Vast expanse of space"
- "Cosmic destiny"
- Generic character names (Alex Chen, Dr. Maya Patel, Jordan Kim)

**❌ Banned Branded Content:**
- Any reference to licensed properties
- Specific faction names from source material
- Branded terminology and phrases
- Character names from source material

### Content Validation Tests

```python
# Example validation pattern used across tests
banned_terms = [
    "emperor", "imperial", "Novel Engine", "40k", "chaos", "orks",
    "space marines", "astra militarum", "adeptus", "krieg",
    "grim darkness", "far future", "41st millennium"
]

for term in banned_terms:
    assert term not in content.lower(), f"Found banned term: {term}"
```

## 📈 Test Coverage Standards

### Current Coverage Status

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| **API Endpoints** | 90%+ | ✅ Comprehensive |
| **Character System** | 85%+ | ✅ Complete |
| **Story Generation** | 80%+ | ✅ Extensive |
| **Integration Workflows** | 75%+ | ✅ Good Coverage |
| **Frontend Components** | 70%+ | ✅ Adequate |

### Coverage Commands

```bash
# Generate detailed coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html

# Coverage with branch analysis
pytest --cov=. --cov-branch --cov-report=term-missing
```

## 🧪 Test Types & Examples

### 1. API Endpoint Tests

```python
def test_characters_list_returns_generic_characters(self):
    """Verify characters list returns only generic characters"""
    response = client.get("/characters")
    assert response.status_code == 200
    data = response.json()
    
    # Should contain our generic characters
    characters = data["characters"]
    assert "pilot" in characters
    assert "scientist" in characters
    assert "engineer" in characters
    
    # Should NOT contain branded characters
    branded_chars = ["krieg", "ork", "isabella_varr"]
    for branded in branded_chars:
        assert branded not in characters
```

### 2. Story Content Validation

```python
def test_no_branded_content_in_generated_stories(self):
    """Test that generated stories contain no branded content"""
    story = chronicler.transcribe_log(sample_log_path)
    story_lower = story.lower()
    
    # Check for banned branded terms
    for banned_term in BANNED_BRAND_TERMS:
        assert banned_term not in story_lower, \
            f"Banned term '{banned_term}' found in story"
    
    # Verify sci-fi content present
    sci_fi_terms = ["space", "galaxy", "research", "technology"]
    has_sci_fi = any(term in story_lower for term in sci_fi_terms)
    assert has_sci_fi, "Story should contain sci-fi elements"
```

### 3. Character System Validation

```python
def test_no_branded_content_in_characters(self):
    """Test that no branded content exists in character files"""
    for char_name in GENERIC_CHARACTERS:
        char_dir = CHARACTER_DIR / char_name
        
        for md_file in char_dir.glob("*.md"):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            for term in branded_terms:
                assert term not in content, \
                    f"Branded term '{term}' found in {md_file}"
```

### 4. Integration Workflow Tests

```python
def test_end_to_end_simulation_workflow(self):
    """Test complete simulation workflow from API to story generation"""
    # Step 1: Get available characters via API
    char_response = client.get("/characters")
    assert char_response.status_code == 200
    
    # Step 2: Run simulation via API
    sim_response = client.post("/simulations", json=SIMULATION_REQUEST)
    assert sim_response.status_code == 200
    
    # Step 3: Validate integrated results
    story = sim_response.json()["story"]
    assert len(story) > 200
    
    # Step 4: Verify debranding
    story_lower = story.lower()
    for term in banned_terms:
        assert term not in story_lower
```

## 🐛 Test-Driven Debugging

### Common Test Failure Patterns

1. **Brand Content Detection**
   ```bash
   # Find remaining branded content
   grep -r -i "emperor\|imperial\|Novel Engine" . --exclude-dir=node_modules
   ```

2. **API Response Validation**
   ```bash
   # Test API manually
   curl -X GET "http://127.0.0.1:8000/characters"
   curl -X POST "http://127.0.0.1:8000/simulations" -H "Content-Type: application/json" -d '{"character_names": ["pilot", "scientist"]}'
   ```

3. **Character Loading Issues**
   ```python
   # Debug character loading
   from persona_agent import PersonaAgent
   agent = PersonaAgent(character_name="pilot")
   print(agent.character_context[:200])
   ```

### Debugging Commands

```bash
# Run tests with detailed output
pytest -v -s tests/test_api_endpoints_comprehensive.py

# Run single test with debugging
pytest -v -s tests/test_story_generation_comprehensive.py::TestDebrandingValidation::test_no_branded_content_in_generated_stories

# Capture stdout
pytest -s --capture=no

# Run with pdb debugger
pytest --pdb tests/specific_test.py
```

## ⚡ Performance Testing

### Performance Test Categories

```python
def test_story_generation_performance(self):
    """Test story generation performance"""
    start_time = time.time()
    story = chronicler.transcribe_log(sample_log)
    end_time = time.time()
    
    generation_time = end_time - start_time
    assert generation_time < 5.0, f"Generation too slow: {generation_time}s"
    assert len(story) > 100, "Should generate substantial content"
```

### Load Testing

```bash
# Concurrent API testing
pytest -m performance tests/test_api_endpoints_comprehensive.py::TestPerformanceAndLoad -v

# Memory usage testing  
pytest -m performance tests/test_character_system_comprehensive.py::TestPerformanceAndScalability
```

## 🔒 Security Testing

### Security Validation Points

1. **Input Sanitization**
2. **SQL Injection Prevention**  
3. **XSS Protection**
4. **Brand Content Filtering**

```python
def test_input_sanitization(self):
    """Test that inputs are properly sanitized"""
    malicious_request = {
        "character_names": ["pilot", "scientist"],
        "setting": "<script>alert('xss')</script>",
        "scenario": "'; DROP TABLE users; --"
    }
    
    response = client.post("/simulations", json=malicious_request)
    if response.status_code == 200:
        story = response.json()["story"]
        assert "<script>" not in story
        assert "DROP TABLE" not in story
```

## 📝 Adding New Tests

### Test Creation Guidelines

1. **Follow naming conventions**: `test_*.py` for files, `test_*` for functions
2. **Use descriptive names**: Clearly indicate what is being tested
3. **Include docstrings**: Explain the test purpose and validation
4. **Validate debranding**: Always check for brand content removal
5. **Test edge cases**: Include error conditions and boundary cases
6. **Performance awareness**: Include timing assertions where relevant

### New Test Template

```python
def test_new_feature_debranding_validation(self):
    """Test new feature maintains debranding standards"""
    # Setup
    test_data = create_test_scenario()
    
    # Execute
    result = system_under_test.process(test_data)
    
    # Validate functionality
    assert result.status == "success"
    assert len(result.content) > 0
    
    # Validate debranding
    content_lower = result.content.lower()
    for banned_term in BANNED_BRAND_TERMS:
        assert banned_term not in content_lower, \
            f"Found banned term: {banned_term}"
    
    # Validate sci-fi content
    sci_fi_present = any(term in content_lower for term in SCI_FI_TERMS)
    assert sci_fi_present, "Should contain sci-fi elements"
```

## 🚀 Continuous Integration

### CI Pipeline Tests

```bash
# Quick validation suite
pytest -m "not slow" --maxfail=5

# Full test suite
pytest --cov=. --cov-report=xml

# Critical path tests
pytest -m "api or integration" -v
```

### Pre-commit Testing

```bash
# Run before commits
pytest tests/test_api_endpoints_comprehensive.py tests/test_story_generation_comprehensive.py -q
```

## 📚 Test Documentation Standards

### Test Documentation Requirements

1. **Purpose**: What the test validates
2. **Setup**: Required test conditions
3. **Execution**: What actions are performed  
4. **Validation**: What results are checked
5. **Debranding**: How brand content removal is verified

### Documentation Example

```python
def test_comprehensive_example(self):
    """
    Test comprehensive story generation workflow with debranding validation.
    
    Purpose: Validates end-to-end story generation produces high-quality,
    debranded sci-fi content.
    
    Setup: Creates mock campaign log with generic characters.
    Execution: Runs complete story generation pipeline.
    Validation: Checks story quality, length, coherence, and theme.
    Debranding: Ensures no branded terms and confirms sci-fi alternatives.
    """
    # Test implementation...
```

## 🎯 Testing Best Practices

### Do's ✅

- **Test debranding consistently** - Every test should validate brand content removal
- **Use meaningful assertions** - Check specific expected behaviors
- **Include edge cases** - Test error conditions and boundary scenarios
- **Maintain test independence** - Tests should not depend on each other
- **Use descriptive names** - Test names should clearly indicate purpose
- **Document complex tests** - Include docstrings explaining validation logic

### Don'ts ❌

- **Skip debranding validation** - Always check for brand content removal
- **Test implementation details** - Focus on behaviors, not internal structure
- **Create flaky tests** - Ensure consistent, reliable test results
- **Ignore performance** - Include basic performance validation
- **Use hardcoded values** - Use constants and configuration where appropriate

## 📊 Test Results & Reporting

### Current Test Status

```bash
# Generate comprehensive test report
pytest --cov=. --cov-report=html --junitxml=test-results.xml -v

# View HTML coverage report
open htmlcov/index.html

# View test results
open test-results.xml
```

### Success Criteria

- ✅ **API Tests**: 90%+ pass rate
- ✅ **Character Tests**: 95%+ pass rate  
- ✅ **Story Tests**: 85%+ pass rate
- ✅ **Integration Tests**: 80%+ pass rate
- ✅ **Debranding**: 100% compliance required
- ✅ **Performance**: <5s for critical operations

---

## 🎉 Conclusion

The StoryForge AI test suite provides comprehensive validation of our debranded, generic sci-fi story generation platform. Regular testing ensures we maintain high quality while staying true to our generic, universal theme.

For questions or test-related issues, refer to the individual test files or run tests with verbose output for detailed feedback.
