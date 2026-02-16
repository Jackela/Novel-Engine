# ADR-004: Director Mode Workflow Orchestration

**Status**: Accepted
**Date**: 2026-02-03
**Deciders**: Architecture Team

## Context

The Novel Engine requires an author-centric interface for narrative construction that balances creative control with AI assistance. Authors need:

- Granular control over narrative structure (Story → Chapter → Scene → Beat)
- AI-powered suggestions that augment rather than replace creativity
- Visual feedback on narrative pacing and structure
- Multi-dimensional critique for craft improvement

Several architectural patterns were considered for orchestrating the Director Mode workflow.

## Decision

We will implement a hexagonal Director Mode architecture with:

1. **Hierarchical Narrative Model**: Story → Chapter → Scene → Beat (atomic unit)
2. **Six Beat Types**: Action, Dialogue, Reaction, Revelation, Transition, Description
3. **AI-Augmented Editing**: Spark button generates contextual beat suggestions
4. **Multi-Dimensional Critique**: Pacing, Voice, Showing vs. Telling, Dialogue, Structure
5. **Contract-First API**: Backend Pydantic schemas → OpenAPI → Frontend Zod types

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
├─────────────────────────────────────────────────────────────┤
│  Features/Director/                                         │
│  ├── BeatList (micro-editor)                                │
│  ├── PacingGraph (visualization)                            │
│  ├── ConflictPanel (relationship tracking)                  │
│  └── CritiquePanel (craft analysis)                         │
├─────────────────────────────────────────────────────────────┤
│  TanStack Query (server state) + Zustand (UI state)         │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  API Layer (routers/structure.py)                           │
│  ├── CRUD endpoints for Story, Chapter, Scene, Beat         │
│  ├── POST /api/beats/suggest (AI suggestions)               │
│  ├── POST /api/scenes/{id}/critique (craft analysis)        │
│  └── GET /api/chapters/{id}/pacing (pacing metrics)         │
├─────────────────────────────────────────────────────────────┤
│  Services                                                   │
│  ├── PacingService (rhythm analysis)                        │
│  ├── CritiqueService (craft evaluation)                     │
│  └── SuggestionService (beat generation)                    │
├─────────────────────────────────────────────────────────────┤
│  Domain Entities                                            │
│  ├── Story, Chapter, Scene, Beat                            │
│  ├── Conflict, Plotline, Foreshadowing                      │
│  └── MoodShift (emotional tracking)                         │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### 1. Beat System (Atomic Narrative Units)

Beats are the smallest editable unit in Director Mode:

```python
# Backend beat types
class BeatType(str, Enum):
    ACTION = "action"      # Physical events (blue)
    DIALOGUE = "dialogue"  # Character conversations (emerald)
    REACTION = "reaction"  # Character responses (amber)
    REVELATION = "revelation"  # New information (purple)
    TRANSITION = "transition"    # Scene changes (gray)
    DESCRIPTION = "description"  # Setting/exposition (cyan)
```

Each beat contains:
- `content`: The narrative text
- `character_id`: Speaking/acting character (optional)
- `mood_shift`: Emotional impact (-5 to +5)
- `order_index`: Position within scene

#### 2. AI Suggestion Workflow

```
┌──────────────┐    Context Collection    ┌──────────────┐
│   Author     │ ───────────────────────▶ │   Frontend   │
│  (Writer)    │                          │  Component   │
└──────────────┘                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   Spark API  │
                                          │  /suggest    │
                                          └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  AI Service  │
                                          │  - SRE       │
                                          │  - ENE       │
                                          └──────┬───────┘
                                                 │
                                                 ▼
┌──────────────┐    3 Suggestions + Rationale  ┌──────────────┐
│   Author     │ ◀───────────────────────────── │   Response   │
│  (Writer)    │    (Type Badge + Preview)     │     JSON     │
└──────────────┘                                └──────────────┘
```

**Key Integration Points:**
- `SubjectiveRealityEngine`: Provides character-specific context
- `EmergentNarrativeEngine`: Ensures narrative coherence
- `CausalGraph`: Records suggestions as narrative events

#### 3. Critique System

Multi-dimensional analysis with configurable severity thresholds:

| Dimension | Metrics | Severity Levels |
|-----------|---------|-----------------|
| Pacing | Tension variance, energy flow | Info, Warning, Critical |
| Voice | Consistency score, style matches | Low, Medium, High |
| Showing vs. Telling | Abstract/concrete ratio | Percentile |
| Dialogue | Naturalness, character distinctiveness | Score 0-100 |
| Structure | Arc effectiveness, hook strength | Pass/Fail |

#### 4. Pacing Visualization

Dual-area chart implementation:
- **X-axis**: Scene order within chapter
- **Y-axis (left)**: Tension (0-100)
- **Y-axis (right)**: Energy (0-100)
- **Issue markers**: Monotony, spikes, abrupt shifts

## Alternatives Considered

### 1. **Monolithic Editor Component**

A single large component handling all editing operations.

**Pros**:
- Simpler initial implementation
- Shared state management

**Cons**:
- Difficult to maintain (component creep)
- Poor reusability
- Testing complexity
- Hard to optimize performance

**Rejected for**: Micro-editor pattern (BeatList as self-contained component) provides better separation of concerns.

### 2. **Client-Side AI Integration**

Run AI models directly in the browser using WebAssembly.

**Pros**:
- No API latency
- Privacy (data stays local)
- No server costs

**Cons**:
- Limited model capacity (browser constraints)
- Inconsistent experience across devices
- Offline complexity (model loading/caching)
- Cannot leverage shared context (SRE/ENE)

**Rejected for**: Server-side AI enables richer context integration and consistent quality.

### 3. **Real-Time Collaborative Editing**

Multiple authors editing simultaneously like Google Docs.

**Pros**:
- Natural for writing teams
- Immediate feedback

**Cons**:
- Complex conflict resolution (CRDT/OT)
- Heavy infrastructure requirements
- Distracts from single-author workflow focus

**Rejected for**: Director Mode prioritizes individual author craft over collaboration.

### 4. **Freeform Canvas Organization**

Drag-and-drop scenes on a 2D canvas without chapter constraints.

**Pros**:
- Visual flexibility
- Non-linear organization

**Cons**:
- Ambiguous ordering semantics
- Complex export to linear format
- Scanning issues for large works

**Rejected for**: Linear chapter-scene hierarchy maps directly to published novel structure.

## Consequences

### Positive

1. **Granular Control**: Beat-level editing enables precise narrative construction
2. **AI Augmentation**: Spark button provides inspiration without autocompletion
3. **Visual Feedback**: Pacing graphs reveal structural issues invisible in text
4. **Contract Safety**: Pydantic → Zod alignment prevents type drift
5. **Testability**: Hexagonal architecture enables isolated unit testing
6. **Extensibility**: New beat types and critique dimensions can be added

### Negative

1. **Learning Curve**: Authors must learn the beat concept
2. **Overhead**: Simple scenes may not need beat-level granularity
3. **API Latency**: AI suggestions require network calls
4. **Visual Complexity**: Multiple panels can overwhelm new users
5. **Mobile Challenges**: Drag-and-drop requires careful responsive design

### Risks and Mitigation

**Risk**: Beat granularity creates mechanical writing feel
**Mitigation**: Beats are optional for scenes that flow better without them

**Risk**: AI suggestions homogenize narrative voice
**Mitigation**: Suggestions are previews only; author must consciously insert

**Risk**: Pacing metrics reinforce formulaic writing
**Mitigation**: Critique provides observations, not prescriptions; author decides

**Risk**: Large projects (1000+ scenes) impact performance
**Mitigation**: TanStack Query caching + virtualized scrolling in beat lists

## Implementation Notes

### State Management Strategy

| State Type | Solution | Example |
|------------|----------|---------|
| Server Data | TanStack Query | `useBeats(sceneId)` |
| UI Selection | Zustand | `selectedBeatId` |
| Form Drafts | React Hook Form | Beat inline edit |
| Derived | Computed | `moodRunningAverage` |

### API Endpoints

```
# Structure CRUD
GET    /api/stories/{id}
POST   /api/stories
GET    /api/stories/{id}/chapters
POST   /api/chapters
GET    /api/chapters/{id}/scenes
POST   /api/scenes
GET    /api/scenes/{id}/beats
POST   /api/beats
PATCH  /api/beats/{id}
DELETE /api/beats/{id}

# AI Features
POST   /api/beats/suggest
POST   /api/scenes/{id}/critique
GET    /api/chapters/{id}/pacing

# Analysis
GET    /api/stories/{id}/health
GET    /api/chapters/{id}/conflicts
```

### Frontend Component Hierarchy

```
DirectorWorkspace/
├── StoryOutline (tree navigation)
├── ChapterEditor/
│   ├── SceneList (reorderable)
│   └── SceneEditor/
│       ├── SceneMetadata (title, location, phase)
│       ├── BeatList (micro-editor)
│       │   ├── BeatItem (read-only)
│       │   └── BeatEditor (inline edit)
│       ├── ConflictPanel (relationships)
│       └── ForeshadowingTracker
├── PacingPanel (chapter-level visualization)
└── CritiquePanel (scene-level craft analysis)
```

## Related Decisions

- ADR-003: Pydantic schemas define backend contracts
- FE-001: Frontend styling SSOT and server-state standardization
- CIT-005: State management consolidation strategy

## Status Changes

- 2026-02-03: Proposed and accepted as part of Code Citadel documentation effort
