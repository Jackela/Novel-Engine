# Design: Events & Rumors

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURE MAP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Domain Layer (EXISTS - reuse directly)                  │   │
│  │  ├── HistoryEvent (history_event.py - 667 lines)         │   │
│  │  │   ├── EventType: WAR, BATTLE, DISASTER, etc.          │   │
│  │  │   ├── EventSignificance: TRIVIAL → LEGENDARY          │   │
│  │  │   └── ImpactScope: GLOBAL, REGIONAL, LOCAL            │   │
│  │  ├── Rumor (rumor.py - 329 lines)                        │   │
│  │  │   ├── RumorOrigin: EVENT, NPC, PLAYER, UNKNOWN        │   │
│  │  │   ├── truth_value: 0-100 with decay per hop           │   │
│  │  │   └── current_locations: Set[str]                     │   │
│  │  └── Location (location.py - 852 lines)                  │   │
│  │      ├── parent_location_id / child_location_ids         │   │
│  │      └── connections: List[str] for adjacency            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Application Layer (MOSTLY EXISTS)                       │   │
│  │  ├── RumorPropagationService (566 lines - COMPLETE)      │   │
│  │  │   ├── propagate_rumors(): spreads to adjacent         │   │
│  │  │   ├── create_rumor_from_event(): with truth logic     │   │
│  │  │   └── TRUTH_BY_IMPACT mapping                         │   │
│  │  └── RumorPropagationHandler (NEW)                       │   │
│  │      ├── Subscribes to world.time_advanced               │   │
│  │      ├── Calls RumorPropagationService.propagate_rumors  │   │
│  │      └── Isolated failure handling (no FactionTick impact)│  │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Infrastructure Layer (NEW ADAPTERS)                     │   │
│  │  ├── EventRepository Port + InMemoryAdapter              │   │
│  │  ├── RumorRepository Port + InMemoryAdapter              │   │
│  │  └── LocationRepository.find_adjacent() implementation   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  API Layer (NEW ROUTERS)                                 │   │
│  │  ├── GET /api/world/events                               │   │
│  │  ├── POST /api/world/events (manual creation)            │   │
│  │  └── GET /api/world/locations/{id}/rumors                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Frontend Layer (NEW COMPONENTS)                         │   │
│  │  ├── WorldTimeline.tsx - Chronological event feed        │   │
│  │  └── TavernBoard.tsx - Location rumor view               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Event Flow

```
Time Advance Flow:
──────────────────
POST /api/world/time/advance
        │
        ▼
  WorldTimeRouter
        │
        ▼
  TimeService.advance_time()
        │
        ▼
  TimeAdvancedEvent published
        │
        ├──▶ TimeAdvancedHandler ──▶ FactionTickService
        │
        └──▶ RumorPropagationHandler ──▶ RumorPropagationService
                                              │
                                              ▼
                                        propagate_rumors()
                                              │
                                              ├──▶ Get active rumors
                                              ├──▶ Find adjacent locations
                                              ├──▶ Spread with truth decay
                                              └──▶ Save updated rumors
```

## Truth Value Calculation

```python
# Base truth by impact scope
TRUTH_BY_IMPACT = {
    ImpactScope.GLOBAL: 90,
    ImpactScope.REGIONAL: 70,
    ImpactScope.LOCAL: 50,
}

# With ±10% perturbation
import random
base_truth = TRUTH_BY_IMPACT[impact_scope]
perturbed_truth = base_truth + random.randint(-10, 10)
final_truth = max(0, min(100, perturbed_truth))

# Examples:
# GLOBAL event → 80-100% truth (avg 90%)
# REGIONAL event → 60-80% truth (avg 70%)
# LOCAL event → 40-60% truth (avg 50%)
```

## Rumor Propagation Logic

```
Tick Processing:
────────────────
For each active rumor (truth_value > 0):
  For each current_location in rumor.current_locations:
    adjacent = location_repo.find_adjacent(current_location)
    For each adj in adjacent:
      If adj not in rumor.current_locations:
        rumor = rumor.spread_to(adj)  # Creates new instance with decay
  
  If rumor.is_dead (truth_value == 0):
    Delete rumor
  Else:
    Save updated rumor
```

## Frontend Components

### WorldTimeline.tsx
- Vertical chronological list of HistoryEvents
- Sorted by structured_date or date_description
- Visual indicators: significance level, event type icon
- Expandable cards showing full description

### TavernBoard.tsx
- Shows rumors for current location
- Truth indicators: color-coded veracity labels
- Visual style:
  - Confirmed (80-100%): Solid, trustworthy
  - Likely True (60-79%): Slightly transparent
  - Uncertain (40-59%): Question mark icon
  - Likely False (20-39%): Faded, strikethrough
  - False (0-19%): Grayed out

## Error Handling

### EventBus Isolation
- Each handler executes independently
- Failure in RumorPropagationHandler doesn't affect FactionTickService
- Errors logged but don't crash simulation

### Repository Patterns
- In-memory adapters for MVP
- Interface allows future PostgreSQL migration
