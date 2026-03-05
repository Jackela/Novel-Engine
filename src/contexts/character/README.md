# Character Context

## Overview
The Character Context is responsible for managing character entities within the Novel Engine platform. It handles character creation, progression, state management, and all character-related domain logic including stats, skills, memories, goals, and inventory.

This context enforces character consistency rules, manages character lifecycle events, and provides the foundation for AI-driven character behavior through psychological profiles and memory systems.

## Domain

### Aggregates
- **Character**: Root aggregate for character management
  - Maintains consistency across profile, stats, skills, psychology, memories, and goals
  - Enforces business rules: level-appropriate stats, racial ability minimums, class-skill requirements
  - Tracks character lifecycle: creation, leveling, death
  - Location tracking with travel history
  - Inventory management
  - Faction membership

### Entities
- **None**: Character aggregate encapsulates all related data through value objects.

### Value Objects
- **CharacterID**: Unique character identifier with UUID support
- **CharacterProfile**: Immutable character identity (name, race, class, age, level, etc.)
  - Enforces name validation, age-level appropriateness
  - Supports all D&D 5e races and classes plus custom options
  
- **CharacterStats**: Core statistics (abilities, vitals, combat)
  - **CoreAbilities**: STR, DEX, CON, INT, WIS, CHA
  - **VitalStats**: HP, mana, stamina, armor class
  - **CombatStats**: Attack bonuses, damage reduction
  
- **CharacterPsychology**: Big Five personality model
  - Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism
  - Drives AI behavior and dialogue generation
  
- **CharacterMemory**: Immutable experience records
  - Importance scoring for core memory identification
  - Tagging system for memory categorization
  
- **CharacterGoal**: Character objectives with urgency and status
  - Status tracking: ACTIVE, COMPLETED, FAILED
  - Urgency levels: LOW, MEDIUM, HIGH, CRITICAL

- **Skills**: Character abilities organized by categories
  - Categories: Combat, Physical, Intellectual, Magical, Social, Survival, Artistic, Technical

### Domain Events
- **CharacterCreated**: New character initialized
  - Contains: character_id, name, class, level
  
- **CharacterUpdated**: General character update
  - Contains: updated_fields, version change
  
- **CharacterStatsChanged**: Health, mana, or stamina change
  - Contains: old/new health and mana values
  - Helper methods: `is_damage_taken()`, `is_healing()`, `get_damage_amount()`
  
- **CharacterLeveledUp**: Level progression event
  - Contains: old/new level, stat changes, skill points gained
  
- **CharacterDeleted**: Character removal
  - Contains: final_level, deletion reason
  
- **CharacterLocationChanged**: Movement between locations
  - Contains: previous/new location IDs, timestamp

## Application

### Services
- **CharacterApplicationService**: Main character operations
  - `create_character(profile, stats, skills)` - Create new character
  - `update_character_stats(character_id, new_stats)` - Modify stats
  - `add_memory(character_id, memory)` - Record experience
  - `add_goal(character_id, goal)` - Set objective
  - `complete_goal(character_id, goal_id)` - Mark goal achieved
  - `level_up(character_id)` - Progress character level
  - `move_to_location(character_id, location_id)` - Change location
  - `heal(character_id, amount)` / `take_damage(character_id, amount)` - Modify health

- **CharacterReactor**: Event-driven character reactions
  - Responds to world events with character-appropriate reactions
  - Uses psychology profile for reaction generation

- **GenerationService**: AI-assisted character creation
  - `generate_character(concept)` - Create character from description
  - `generate_background(character_id)` - Flesh out backstory

- **ContextLoader**: Prepares character context for AI consumption
  - Aggregates memories, goals, and current state
  - Prioritizes core memories for LLM prompts

### Commands
- **CreateCharacter**: Initialize new character
  - Handler: `CreateCharacterHandler`
  - Validations: Name uniqueness, stat allocation limits
  
- **UpdateStats**: Modify character statistics
  - Handler: `UpdateStatsHandler`
  - Side effects: CharacterStatsChanged event, death check
  
- **AddMemory**: Record character experience
  - Handler: `AddMemoryHandler`
  - Side effects: May trigger goal progress

### Queries
- **GetCharacterSummary**: Retrieve character overview
  - Handler: `GetCharacterSummaryHandler`
  - Performance: Cached for 60 seconds
  
- **GetCharacterContext**: Get AI-ready context package
  - Handler: `GetCharacterContextHandler`
  - Returns: Profile, recent memories, active goals, visible entities

## Infrastructure

### Repositories
- **CharacterRepository**: Character persistence interface
  - Implementation: `PostgresCharacterRepository` with JSONB for flexible attributes
  - Caching: Redis for hot characters
  
- **MemoryStore**: Specialized memory storage
  - Implementation: Vector database for semantic memory search
  - Enables: "Find memories about betrayal"

### External Services
- **LLMCharacterGenerator**: AI-assisted character creation
  - Uses AI Context for generation requests
  - Implements character concept prompts

## API

### REST Endpoints
- `POST /api/characters` - Create character
- `GET /api/characters/{id}` - Get character details
- `PUT /api/characters/{id}/stats` - Update statistics
- `POST /api/characters/{id}/memories` - Add memory
- `GET /api/characters/{id}/memories` - List memories
- `POST /api/characters/{id}/goals` - Add goal
- `PUT /api/characters/{id}/goals/{goal_id}/complete` - Complete goal
- `POST /api/characters/{id}/level-up` - Level progression

### WebSocket Events
- `character.updated` - Real-time character state changes
- `character.damaged` - Combat event notification

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/character/unit/ -v

# Integration tests
pytest tests/contexts/character/integration/ -v

# All context tests
pytest tests/contexts/character/ -v
```

### Test Coverage
Current coverage: 75%
Target coverage: 85%

## Architecture Decision Records
- ADR-001: Character as aggregate root with immutable profile
- ADR-002: Psychology model (Big Five) for AI behavior
- ADR-003: Memory system with importance scoring
- ADR-004: Travel history tracking for narrative continuity

## Integration Points

### Inbound
- Events consumed:
  - `WorldStateChanged` from World Context (location changes)
  - `ItemEquipped` from Inventory Context (stat modifiers)
  - `SpellEffectApplied` from Magic Context (temporary changes)

### Outbound
- Events published:
  - `CharacterCreated` - For campaign auto-add
  - `CharacterStatsChanged` - For UI updates, death detection
  - `CharacterLocationChanged` - For world state updates
  - `GoalCompleted` - For quest progression

### Dependencies
- **Domain**: None (pure domain)
- **Application**: AI Context (generation), World Context (locations)
- **Infrastructure**: PostgreSQL, Redis, Vector DB

## Development Guide

### Adding New Features
1. Extend domain model (value objects or aggregate methods)
2. Add application service methods
3. Update repository if persistence changes
4. Add API endpoints if needed
5. Write tests

### Common Tasks
- **Adding a new race**: Extend `CharacterRace` enum and update `_validate_racial_abilities()`
- **Adding a new class**: Extend `CharacterClass` enum and update `_validate_class_skills()`
- **Adding new stat types**: Add to `CharacterStats`, update validation
- **Adding memory types**: Extend `MemoryType` enum and context assembly

## Maintainer
Team: @character-team
Contact: characters@example.com
