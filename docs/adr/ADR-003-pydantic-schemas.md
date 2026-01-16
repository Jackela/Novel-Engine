# ADR-003: Pydantic Schema Architecture

**Status**: Accepted  
**Date**: 2025-08-11  
**Deciders**: Architecture Team  

## Context

The Novel Engine requires robust data validation and serialization for:

- API request/response validation with clear error messages
- Type safety across the multi-agent system
- Schema evolution and versioning support
- Integration with FastAPI for automatic API documentation
- Performance optimization through efficient serialization
- Developer experience with IDE support and error checking

The system handles complex nested data structures (WorldState, PersonaCardV2, CharacterAction) that need consistent validation across all components.

## Decision

We will use **Pydantic v2** as the foundation for all data schemas in the Novel Engine, with a single source of truth approach:

### Core Design Principles

**Single Source of Truth**: All schemas defined in `src/core/types/shared_types.py`  
**Comprehensive Validation**: Use Pydantic's constraint system for all business rules  
**Type Safety**: Full type annotations with strict validation  
**API Integration**: Native FastAPI integration for request/response validation  
**Performance**: Leverage Pydantic v2's Rust core for validation speed  

### Schema Organization
- **Core Models**: PersonaCardV2, WorldState, TurnBrief, CharacterAction
- **Supporting Models**: Entity, Fact, Relation, Doctrine, etc.
- **Constraint Validation**: Field-level validation with clear error messages
- **Versioning**: Schema version tracking with backward compatibility

## Alternatives Considered

### 1. **Python dataclasses**
Use standard library dataclasses for data structures.

**Pros**:
- No external dependencies
- Simple, lightweight implementation
- Good IDE support for type hints
- Fast instantiation performance

**Cons**:
- No runtime validation (type hints are ignored at runtime)
- Manual serialization/deserialization required
- No automatic API documentation generation
- No constraint validation (e.g., ranges, patterns)
- Poor error messages for invalid data

### 2. **attrs + cattrs**
Use attrs for data classes with cattrs for serialization.

**Pros**:
- Flexible attribute definition
- Good performance characteristics
- Powerful conversion system with cattrs
- Mature and stable ecosystem

**Cons**:
- Two-library dependency for full functionality
- Manual validation logic required
- No FastAPI integration
- Complex setup for nested validation
- Less mainstream adoption than Pydantic

### 3. **Custom Validation Classes**
Build custom base classes with validation logic.

**Pros**:
- Complete control over validation behavior
- Optimized for specific use cases
- No external dependencies
- Custom error message formats

**Cons**:
- Significant development and maintenance overhead
- Error-prone custom validation logic
- No ecosystem tools or integrations
- Reinventing well-solved problems
- Poor developer experience compared to established solutions

### 4. **Protocol Buffers (protobuf)**
Use Google's Protocol Buffers for schema definition.

**Pros**:
- Excellent performance for large datasets
- Strong schema evolution support
- Language-agnostic schema definitions
- Compact binary serialization

**Cons**:
- Complex development workflow (code generation required)
- Poor integration with Python ecosystem
- Limited validation capabilities
- Overkill for JSON API scenarios
- Difficult debugging (binary format)

## Consequences

### Positive

1. **Type Safety**: Full runtime validation of all data structures
2. **API Integration**: Automatic FastAPI request/response validation
3. **Developer Experience**: Excellent IDE support with auto-completion and error detection
4. **Clear Error Messages**: Detailed validation errors with field-specific information
5. **Performance**: Pydantic v2 provides excellent validation performance
6. **Documentation**: Automatic API documentation generation from schemas
7. **Ecosystem**: Rich ecosystem of tools and integrations
8. **Schema Evolution**: Built-in support for version migration and compatibility
9. **Serialization**: Efficient JSON serialization/deserialization
10. **Testing**: Easy to create valid/invalid test data

### Negative

1. **External Dependency**: Adds Pydantic as a required dependency
2. **Learning Curve**: Developers need to learn Pydantic-specific patterns
3. **Validation Overhead**: Runtime validation adds computational cost
4. **Memory Usage**: Validation and schema metadata increase memory footprint
5. **Complex Validation**: Very complex validation rules can be difficult to express

### Risks and Mitigation

**Risk**: Pydantic validation performance bottlenecks  
**Mitigation**: Use Pydantic v2 with Rust core, profile critical paths, cache validation results

**Risk**: Schema evolution breaking backward compatibility  
**Mitigation**: Implement versioning strategy, maintain migration paths, comprehensive testing

**Risk**: Complex nested validation becomes unmaintainable  
**Mitigation**: Keep validation rules simple and well-documented, use composition over complexity

## Implementation Details

### Schema Definition Pattern
```python
# src/core/types/shared_types.py
from pydantic import BaseModel, Field, constr
from typing import List, Optional, Literal

class PersonaCardV2(BaseModel):
    """Complete agent definition with validation."""
    id: constr(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    faction: constr(min_length=1)
    beliefs: List[Belief] = Field(..., min_length=1)
    knowledge_scope: List[KnowledgeScope] = Field(..., min_length=1)
    # ... other fields with appropriate constraints
```

### Validation Constraints
- **String Constraints**: `constr()` for patterns, length limits
- **Numeric Constraints**: `Field()` with `ge`, `le` for ranges  
- **List Constraints**: `min_length`, `max_length` for list validation
- **Custom Validators**: `@field_validator` for complex business rules

### Error Handling
```python
from pydantic import ValidationError
from fastapi import HTTPException

try:
    action = CharacterAction(**request_data)
except ValidationError as e:
    raise HTTPException(status_code=422, detail=e.errors())
```

### Testing Pattern
```python
def test_persona_validation():
    # Valid data should pass
    valid_persona = PersonaCardV2(
        id="test_agent",
        faction="rebels", 
        beliefs=[{"proposition": "Freedom", "weight": 0.9}],
        knowledge_scope=[{"channel": "visual", "range": 5}]
    )
    
    # Invalid data should raise ValidationError
    with pytest.raises(ValidationError):
        PersonaCardV2(id="")  # Empty ID should fail
```

### Performance Optimization
- **Model Caching**: Cache compiled models for repeated use
- **Selective Validation**: Use `validate_assignment=False` for performance-critical paths
- **Batch Validation**: Validate lists of items efficiently
- **Schema Compilation**: Pre-compile schemas at application startup

### Schema Versioning
```python
class PersonaCardV2(BaseModel):
    """Version 2 of PersonaCard with expanded capabilities."""
    model_config = ConfigDict(
        json_schema_extra = {
            "version": "2.0",
            "deprecated_fields": ["legacy_field"],
            "migration_notes": "Use beliefs instead of legacy_field"
        }
    )
```

## Integration Points

### FastAPI Integration
```python
from fastapi import FastAPI
from src.core.types.shared_types import CharacterAction, WorldState

app = FastAPI()

@app.post("/simulations/{run_id}/turn")
async def execute_turn(
    run_id: str, 
    actions: List[CharacterAction]  # Automatic validation
) -> dict:
    # Actions are validated by FastAPI using Pydantic schema
    pass
```

### Testing Integration
- **Fixture Generation**: Use Pydantic to generate valid test data
- **Error Testing**: Systematically test all validation constraints
- **Schema Testing**: Validate schema evolution and migration

### Documentation Integration
- **OpenAPI**: Automatic API documentation from Pydantic models
- **JSON Schema**: Export schemas for external tool integration
- **Type Hints**: Full IDE support for development

## Migration Strategy

### From Existing Code
1. **Identify Data Structures**: Catalog all data classes and dictionaries
2. **Define Schemas**: Create Pydantic models with appropriate constraints
3. **Gradual Migration**: Replace data structures incrementally
4. **Validation Testing**: Ensure all edge cases are covered
5. **Performance Testing**: Validate acceptable performance characteristics

### Schema Evolution
1. **Version Tracking**: Include version metadata in schemas
2. **Backward Compatibility**: Support multiple versions during transitions
3. **Migration Scripts**: Automated data migration for breaking changes
4. **Deprecation Process**: Clear timeline for removing old schema versions

## Related Decisions
- ADR-001: Iron Laws use Pydantic models for action validation
- ADR-002: Fog of War uses Pydantic models for world state filtering  
- ADR-004: Context Supply Chain uses Pydantic models throughout data flow

## Status Changes
- 2025-08-11: Proposed and accepted during initial architecture design



