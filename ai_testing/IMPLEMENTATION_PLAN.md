# LLM Integration Implementation Plan

## Phase 1: Core LLM Infrastructure (Immediate)

### 1.1 Create LLM Client (Priority: CRITICAL)
```python
# ai_testing/llm_client.py
class GeminiClient:
    def __init__(self):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        self.model = "gemini-2.0-flash-exp"
        
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        # Actual API call to Gemini
        pass
```

### 1.2 Prompt Engineering System
```python
# ai_testing/prompt_builder.py
class PromptBuilder:
    def build_dialogue_prompt(self, character, context, emotion):
        """Build dynamic prompt for dialogue generation"""
        
    def build_event_prompt(self, story_state, event_type):
        """Build prompt for event generation"""
        
    def build_narrative_prompt(self, events, style):
        """Build prompt for narrative prose"""
```

### 1.3 Response Parser
```python
# ai_testing/response_parser.py
class ResponseParser:
    def parse_dialogue(self, llm_output: str) -> DialogueResponse
    def parse_event(self, llm_output: str) -> EventResponse
    def validate_output(self, output: str) -> bool
```

## Phase 2: Character-Driven Generation

### 2.1 Character State → Prompt Mapping
```python
class CharacterPromptAdapter:
    def personality_to_prompt(self, personality: Dict[str, float]) -> str:
        """Convert personality vector to prompt instructions"""
        
    def emotion_to_prompt(self, emotion: EmotionalState) -> str:
        """Convert emotional state to generation guidance"""
        
    def relationship_to_prompt(self, relationships: Dict) -> str:
        """Include relationship context in prompts"""
```

### 2.2 Dynamic Dialogue Generation
```python
class AIDialogueEngine:
    def generate_dialogue(self, speaker: Character, context: StoryContext) -> str:
        prompt = self.build_character_aware_prompt(speaker, context)
        response = self.llm_client.generate(prompt)
        return self.parse_and_validate(response)
```

## Phase 3: Event Generation System

### 3.1 Replace Template-Based Events
```python
class AIEventGenerator:
    def generate_event(self, event_type: str, context: StoryContext) -> Event:
        # NO templates, NO random.choice
        prompt = self.build_event_prompt(event_type, context)
        return self.llm_client.generate_event(prompt)
```

### 3.2 Story Coherence Manager
```python
class StoryCoherenceManager:
    def __init__(self):
        self.story_memory = []  # Key events and facts
        self.plot_graph = PlotGraph()  # Causal relationships
        
    def add_to_context(self, event: Event):
        """Update story context with new event"""
        
    def get_context_for_generation(self) -> str:
        """Prepare context for LLM prompt"""
```

## Migration Strategy

### Step 1: Parallel Implementation (Week 1)
- Keep existing template system running
- Build LLM system alongside
- A/B test outputs

### Step 2: Gradual Replacement (Week 2)
1. Replace dialogue generation first
2. Then event generation
3. Finally narrative transformation

### Step 3: Template Removal (Week 3)
- Remove all template-based generators
- Delete repetition detection (not needed with LLM)
- Clean up fake metrics

## Testing Strategy

### Unit Tests
```python
def test_llm_generates_unique_dialogue():
    """Same context → different outputs"""
    
def test_character_personality_affects_output():
    """Different personalities → different styles"""
    
def test_emotional_state_influences_content():
    """Emotion changes → content changes"""
```

### Integration Tests
```python
def test_full_dialogue_sequence():
    """Generate coherent conversation"""
    
def test_story_progression():
    """Events advance plot logically"""
```

### Quality Tests
```python
def test_dialogue_authenticity():
    """Measure naturalness of generated dialogue"""
    
def test_character_consistency():
    """Check if character voice remains consistent"""
```

## File Structure Changes

### New Files to Create
```
ai_testing/
├── llm/
│   ├── __init__.py
│   ├── gemini_client.py      # Gemini API integration
│   ├── prompt_builder.py     # Dynamic prompt construction
│   ├── response_parser.py    # Parse and validate LLM output
│   └── context_manager.py    # Manage generation context
├── generation/
│   ├── dialogue_generator.py # LLM-based dialogue
│   ├── event_generator.py    # LLM-based events
│   └── narrative_generator.py # LLM-based prose
```

### Files to Deprecate
```
❌ content_variation_system.py  # Template system
❌ advanced_repetition_detector.py # Not needed with LLM
❌ event_types_expansion.py (current template version)
```

### Files to Refactor
```
✏️ dialogue_engine.py → ai_dialogue_engine.py
✏️ event_orchestrator.py → ai_event_orchestrator.py
✏️ quality_enhancer.py → generation_quality.py
```

## Dependencies

### Required Libraries
```python
# requirements.txt additions
google-generativeai>=0.3.0  # Gemini API
openai>=1.0.0               # Backup option
anthropic>=0.18.0           # Alternative option
tiktoken>=0.5.0             # Token counting
langchain>=0.1.0            # Optional: prompt management
```

## Configuration

### Environment Variables
```bash
# .env
GEMINI_API_KEY=your_key_here
DEFAULT_MODEL=gemini-2.0-flash-exp
MAX_TOKENS=2000
TEMPERATURE=0.7
TOP_P=0.9
```

### Model Settings
```python
MODEL_CONFIG = {
    'gemini': {
        'model': 'gemini-2.0-flash-exp',
        'max_tokens': 2000,
        'temperature': 0.7,
        'top_p': 0.9
    },
    'openai': {
        'model': 'gpt-4-turbo-preview',
        'max_tokens': 2000,
        'temperature': 0.7
    }
}
```

## Success Metrics

### Week 1 Goals
- [ ] Working LLM client with Gemini
- [ ] Basic dialogue generation (no templates)
- [ ] Character personality affects output

### Week 2 Goals
- [ ] Event generation via LLM
- [ ] Context management working
- [ ] Emotional states influence content

### Week 3 Goals
- [ ] Full story generation pipeline
- [ ] All templates removed
- [ ] Quality metrics implemented

## Risk Mitigation

### API Failures
- Implement retry logic with exponential backoff
- Cache successful generations
- Fallback to different model if needed

### Quality Issues
- Implement output validation
- Use temperature control
- Multi-pass generation with selection

### Cost Management
- Monitor token usage
- Implement caching layer
- Use smaller models for drafts

## Next Immediate Action

1. Create `llm/gemini_client.py` with basic API integration
2. Test connection and basic generation
3. Create simple dialogue prompt and test
4. Compare output with template system
5. Document results and iterate