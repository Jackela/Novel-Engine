# Narratives Context

## Overview
The Narratives Context provides high-level narrative architecture and story arc management for the Novel Engine platform. It handles the macro-level story structure including narrative arcs, plot points, themes, and pacing management across the entire narrative experience.

This context complements the Narrative Context by focusing on story architecture (arcs, themes, plot structures) rather than content organization (chapters, scenes).

## Domain

### Aggregates
- **NarrativeArc**: Root aggregate for story arcs
  - Manages plot points, themes, pacing segments
  - Character involvement tracking (primary/supporting)
  - Parent/child arc relationships
  - Status lifecycle: planning → active → paused → completed → archived
  - Quality metrics: coherence, thematic consistency, pacing effectiveness

### Entities
- **NarrativeThread**: Continuity thread across arcs
  - Character-specific or theme-specific threads
  - Cross-arc reference tracking
  
- **StoryElement**: Reusable narrative components
  - Set pieces, dramatic situations, character moments

### Value Objects
- **NarrativeId**: Unique arc identifier
- **NarrativeContext**: Setting/context for arc segments
  - Temporal, spatial, atmospheric conditions
  - Applicability ranges (sequence numbers)
  
- **PlotPoint**: Dramatic beats within arcs
  - Type: INCITING_INCIDENT, RISING_ACTION, CLIMAX, RESOLUTION, etc.
  - Importance: MAJOR, MINOR, BACKGROUND
  - Prerequisite events for coherence
  
- **NarrativeTheme**: Thematic elements
  - Type: REDEMPTION, BETRAYAL, LOVE, SACRIFICE, etc.
  - Intensity: SUBTLE, MODERATE, STRONG, DOMINANT
  - Symbolic elements tracking
  
- **StoryPacing**: Pacing configuration for arc segments
  - Type: FAST, MODERATE, SLOW, VARIABLE
  - Intensity levels across sequences

### Domain Events
- **NarrativeArcCreated**: New arc initialized
  - Contains: arc_id, name, type, expected length
  
- **PlotPointAdded**: Dramatic beat added
  - Contains: plot_point_id, type, sequence order, characters involved
  
- **ThemeIntroduced**: New theme added to arc
  - Contains: theme_id, type, introduction sequence
  
- **PacingAdjusted**: Pacing configuration changed
  - Contains: segment_id, previous/new pacing types

## Application

### Services
- **NarrativeArcApplicationService**: Main arc operations
  - `create_arc(name, type, target_length)` - Initialize arc
  - `add_plot_point(arc_id, plot_point)` - Add dramatic beat
  - `add_theme(arc_id, theme)` - Introduce theme
  - `add_pacing_segment(arc_id, pacing)` - Configure pacing
  - `start_arc(arc_id, start_sequence)` - Activate arc
  - `complete_arc(arc_id, end_sequence)` - Mark complete
  - `get_arc_summary(arc_id)` - Comprehensive overview

- **NarrativeFlowService**: Arc progression analysis
  - `analyze_flow(arc_id)` - Assess narrative momentum
  - `suggest_plot_points(arc_id)` - AI-assisted beat suggestions

- **CausalGraphService**: Plot coherence analysis
  - `build_causal_graph(arc_id)` - Map event dependencies
  - `validate_coherence(arc_id)` - Check for plot holes

- **StoryArcManager**: Cross-arc coordination
  - `find_arc_connections(arc_ids)` - Discover relationships
  - `suggest_arc_order(arcs)` - Optimal sequencing

- **PacingManager**: Pacing optimization
  - `analyze_pacing(arc_id)` - Identify pacing issues
  - `recommend_adjustments(arc_id)` - Suggest improvements

- **NarrativePlanningEngine**: AI-assisted planning
  - `generate_arc_outline(concept)` - Create arc from description
  - `expand_plot_point(point_id)` - Flesh out beats

### Commands
- **CreateNarrativeArc**: Initialize arc
  - Handler: `CreateNarrativeArcHandler`
  
- **AddPlotPoint**: Add dramatic beat
  - Handler: `AddPlotPointHandler`
  
- **ActivateArc**: Start arc execution
  - Handler: `ActivateArcHandler`

### Queries
- **GetNarrativeArc**: Arc details
  - Handler: `GetNarrativeArcHandler`
  
- **GetArcsForCharacter**: Character's arcs
  - Handler: `GetArcsForCharacterHandler`
  
- **GetActiveThemes**: Currently active themes
  - Handler: `GetActiveThemesHandler`

## Infrastructure

### Repositories
- **NarrativeArcRepository**: Arc persistence
  - Port: `NarrativeArcRepositoryPort`
  
- **NarrativeThreadRepository**: Thread storage

### External Services
- None directly

## API

### REST Endpoints
- `POST /api/narratives/arcs` - Create arc
- `GET /api/narratives/arcs/{id}` - Get arc details
- `POST /api/narratives/arcs/{id}/plot-points` - Add plot point
- `POST /api/narratives/arcs/{id}/themes` - Add theme
- `PUT /api/narratives/arcs/{id}/start` - Start arc
- `PUT /api/narratives/arcs/{id}/complete` - Complete arc

### WebSocket Events
- `narrative.arc_started` - Real-time updates

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/narratives/unit/ -v

# Integration tests
pytest tests/contexts/narratives/integration/ -v

# All context tests
pytest tests/contexts/narratives/ -v
```

### Test Coverage
Current coverage: 70%
Target coverage: 80%

## Architecture Decision Records
- ADR-001: NarrativeArc as aggregate for story architecture
- ADR-002: Causal graph for plot coherence
- ADR-003: Theme intensity tracking for dramatic balance

## Integration Points

### Inbound
- Events consumed:
  - `CharacterCreated` from Character Context (arc initiation)
  - `CampaignStarted` from Campaigns Context (arc activation)

### Outbound
- Events published:
  - `NarrativeArcCreated` - For planning UI
  - `PlotPointReached` - For world/character reactions
  - `ThemeIntroduced` - For symbolism tracking

### Dependencies
- **Domain**: None (pure domain)
- **Application**: AI Context (planning suggestions)
- **Infrastructure**: PostgreSQL

## Development Guide

### Adding New Features
1. Extend domain models (plot point types, theme types)
2. Add service methods
3. Update repositories
4. Write tests

## Maintainer
Team: @narratives-team
Contact: narratives@example.com
