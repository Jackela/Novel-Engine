# Story Context

## Overview
The Story Context manages scene generation and narrative content creation within the Novel Engine platform. It provides the bridge between high-level narrative structure and actual generated story content.

This context focuses on content generation (scenes, descriptions, dialogue) rather than structure (which is handled by Narrative Context). It coordinates AI services for creative writing while maintaining domain separation.

## Domain

### Aggregates
- **None**: This context is primarily service-oriented.

### Entities
- **None**: Uses value objects for domain concepts.

### Value Objects
- **SceneGenerationResult**: Generated scene content
  - `title`: Scene heading
  - `content`: Full markdown story text
  - `summary`: Short description for UI
  - `visual_prompt`: Description for image generation
  
- **SceneContext**: Input context for generation
  - Characters present
  - Setting details
  - Narrative goals
  - Tone/style requirements

### Domain Events
- **None**: Generation events handled through application layer.

## Application

### Services
- **SceneService**: Scene generation orchestration
  - `generate_scene(context)` - Create scene from context
  - `regenerate_scene(scene_id, adjustments)` - Regenerate with changes
  - `summarize_scene(content)` - Create brief description

- **ContextAssembler**: Preparation for generation
  - `assemble_scene_context(story_id, scene_id)` - Gather context
  - `prioritize_context_elements(context, token_budget)` - Fit to budget
  - `format_for_generation(context)` - AI-ready formatting

### Ports (Interfaces)
- **SceneGeneratorPort**: Abstract scene generation
  - `generate(context)` - Generate scene content
  - `estimate_tokens(context)` - Predict token usage

### Commands
- **GenerateScene**: Request scene creation
  - Handler: `GenerateSceneHandler`
  
- **RegenerateScene**: Request revision
  - Handler: `RegenerateSceneHandler`

### Queries
- **GetSceneContent**: Retrieve generated scene
  - Handler: `GetSceneContentHandler`

## Infrastructure

### Repositories
- **SceneRepository**: Generated content storage

### External Services
- **LLMSceneGenerator**: AI scene generation
  - Implementation: OpenAI/GPT-4 or Claude
  - Prompt engineering for narrative quality
  - Temperature and style control

## API

### REST Endpoints
- `POST /api/story/scenes/generate` - Generate new scene
- `POST /api/story/scenes/{id}/regenerate` - Regenerate scene
- `GET /api/story/scenes/{id}` - Get scene content

### WebSocket Events
- `story.scene_generated` - Generation complete

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/story/unit/ -v

# Integration tests
pytest tests/contexts/story/integration/ -v

# All context tests
pytest tests/contexts/story/ -v
```

### Test Coverage
Current coverage: 60%
Target coverage: 80%

## Architecture Decision Records
- ADR-001: Port-adapter pattern for generator flexibility
- ADR-002: Context assembler for token budget management

## Integration Points

### Inbound
- Events consumed:
  - `SceneRequired` from Narrative Context

### Outbound
- Events published:
  - `SceneGenerated` - For narrative integration

### Dependencies
- **Domain**: None (pure domain)
- **Application**: AI Context (generation), Narrative Context (structure)
- **Infrastructure**: LLM APIs

## Development Guide

### Adding New Features
1. Extend value objects for new content types
2. Add generation service methods
3. Update generator implementations
4. Write tests

## Maintainer
Team: @story-team
Contact: story@example.com
