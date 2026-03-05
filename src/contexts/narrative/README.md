# Narrative Context

## Overview
The Narrative Context manages story structure at the chapter and scene level within the Novel Engine platform. It provides the domain model for organizing narrative content hierarchically, from stories down to individual beats.

This context handles story creation, chapter management, scene organization, pacing analysis, and plot structure. It serves as the structural backbone for generated and authored narrative content.

## Domain

### Aggregates
- **Story**: Root aggregate representing a complete narrative work
  - Owns chapters and enforces structural consistency
  - Tracks publication status (DRAFT, PUBLISHED)
  - Manages chapter ordering and uniqueness

### Entities
- **Chapter**: Major narrative division
  - Contains scenes, plotlines, conflicts
  - Order index for positioning within story
  - Completion status tracking
  
- **Scene**: Individual narrative unit
  - Setting, characters present, narrative content
  - Links to world locations
  
- **Beat**: Smallest narrative unit
  - Individual dramatic beat within a scene
  - Type: ACTION, REACTION, DECISION, DISCOVERY
  
- **Plotline**: Through-line tracking
  - Progress across chapters/scenes
  - Status: INTRODUCED, DEVELOPING, CLIMAX, RESOLVED
  
- **Conflict**: Dramatic tension element
  - Type: INTERNAL, EXTERNAL, INTERPERSONAL
  - Stakes and resolution tracking
  
- **Foreshadowing**: Setup for future events
  - Target event reference
  - Payoff tracking

### Value Objects
- **StoryStatus**: DRAFT, PUBLISHED
- **ChapterType**: PROLOGUE, ACT_BREAK, CHAPTER, EPILOGUE
- **BeatType**: ACTION, REACTION, DECISION, DISCOVERY, REVELATION
- **Pacing**: Scene-level pacing indicator (FAST, MODERATE, SLOW)

### Domain Events
- **StoryCreated**: New story initialized
- **ChapterAdded**: Chapter added to story
- **SceneCreated**: New scene added
- **BeatAdded**: Dramatic beat recorded
- **StoryPublished**: Story moved to published state

## Application

### Services
- **ChapterAnalysisService**: Structural analysis
  - `analyze_structure(story_id)` - Identify structural issues
  - `detect_pacing_problems(story_id)` - Find pacing inconsistencies
  - `suggest_improvements(story_id)` - AI-assisted suggestions

- **PacingService**: Pacing management
  - `calculate_pacing(story_id)` - Analyze scene-to-scene pacing
  - `suggest_pacing_adjustments(story_id)` - Recommend changes

### Commands
- **CreateStory**: Initialize story
  - Handler: `CreateStoryHandler`
  
- **AddChapter**: Add chapter to story
  - Handler: `AddChapterHandler`
  
- **PublishStory**: Move to published state
  - Handler: `PublishStoryHandler`

### Queries
- **GetStoryStructure**: Complete structural view
  - Handler: `GetStoryStructureHandler`
  
- **GetChapterSummary**: Chapter overview
  - Handler: `GetChapterSummaryHandler`

## Infrastructure

### Repositories
- **NarrativeRepository**: Story persistence
  - Implementation: `InMemoryNarrativeRepository` (current)
  - Planned: PostgreSQL with hierarchical storage

### External Services
- None directly

## API

### REST Endpoints
- `POST /api/narratives/stories` - Create story
- `GET /api/narratives/stories/{id}` - Get story details
- `POST /api/narratives/stories/{id}/chapters` - Add chapter
- `GET /api/narratives/stories/{id}/structure` - Get full structure
- `POST /api/narratives/stories/{id}/publish` - Publish story

### WebSocket Events
- `narrative.chapter_added` - Real-time updates

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/narrative/unit/ -v

# Integration tests
pytest tests/contexts/narrative/integration/ -v

# All context tests
pytest tests/contexts/narrative/ -v
```

### Test Coverage
Current coverage: To be measured
Target coverage: 80%

## Architecture Decision Records
- ADR-001: Story as aggregate root for narrative hierarchy
- ADR-002: Beat-level granularity for dramatic analysis

## Integration Points

### Inbound
- Events consumed:
  - `SceneGenerated` from Story Context (structural integration)

### Outbound
- Events published:
  - `StoryPublished` - For content delivery

### Dependencies
- **Domain**: None (pure domain)
- **Application**: Story Context (scene content)
- **Infrastructure**: PostgreSQL (planned)

## Development Guide

### Adding New Features
1. Extend domain entities for new structural elements
2. Add analysis service methods
3. Update repository for new queries
4. Write tests

## Maintainer
Team: @narrative-team
Contact: narrative@example.com
