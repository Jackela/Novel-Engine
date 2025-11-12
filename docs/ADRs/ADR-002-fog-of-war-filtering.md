# ADR-002: Fog of War Information Filtering

**Status**: Accepted  
**Date**: 2025-08-11  
**Deciders**: Architecture Team  

## Context

In multi-agent narrative simulations, agents should not have omniscient knowledge of the world state. Realistic limitations on information access are necessary to:

- Create more engaging narratives with uncertainty and discovery
- Prevent agents from making decisions based on information they shouldn't have
- Support different information-gathering capabilities (visual, radio, intelligence)
- Enable stealth, surprise, and hidden information mechanics

The system needs to determine what information each agent can access based on their capabilities and position.

## Decision

We will implement a "Fog of War" information filtering system that limits each agent's view of the world state based on their defined `knowledge_scope` capabilities.

### Core Design

**Knowledge Scope Channels**:
- **Visual**: Direct line-of-sight observation with range limits
- **Radio**: Communication-based information sharing with technical range limits  
- **Intel**: Intelligence gathering and faction-based information sharing

**Filtering Process**:
1. **Entity Filtering**: Only entities within scope are visible to the agent
2. **Fact Filtering**: Only facts about visible entities are included
3. **Turn Brief Generation**: Create personalized, limited world view for each agent
4. **Provenance Tracking**: All information includes source attribution

**Implementation Location**: `DirectorAgent._build_turn_brief()` method applies filtering before agent decision-making.

## Alternatives Considered

### 1. **Transparent World State**
Provide all agents with complete world state information.

**Pros**:
- Simple implementation (no filtering required)
- Agents can make fully-informed decisions
- No performance overhead for filtering
- Easy debugging (all agents see same data)

**Cons**:
- Unrealistic omniscience breaks narrative immersion
- No possibility for stealth, surprise, or discovery mechanics
- Agents would never make "mistakes" due to incomplete information
- Less interesting tactical gameplay
- No differentiation between agent capabilities

### 2. **LLM-Based Information Filtering**
Use the LLM to determine what information an agent would realistically know.

**Pros**:
- Natural language reasoning about information access
- Flexible adaptation to complex scenarios
- Could consider subtle social and contextual factors

**Cons**:
- Non-deterministic results (same scenario filtered differently)
- High computational cost (LLM call for every information item)
- Difficult to debug information access decisions
- Inconsistent filtering could break game mechanics
- Token costs scale with world complexity

### 3. **Physics-Based Line of Sight**
Implement detailed 3D visibility calculations with ray-casting.

**Pros**:
- Highly realistic visual occlusion
- Precise distance and obstacle calculations
- Established algorithms and libraries available

**Cons**:
- Massive computational overhead for narrative simulation
- Requires detailed 3D world modeling
- Overkill for abstract narrative mechanics
- Complex edge case handling (mirrors, indirect lighting, etc.)
- Limited to visual information only

### 4. **Zone-Based Information Sharing**
Divide the world into information zones with predefined sharing rules.

**Pros**:
- Simple to implement and understand
- Predictable information flow
- Good performance characteristics
- Easy to visualize and debug

**Cons**:
- Limited flexibility for complex scenarios
- Artificial boundaries may feel unrealistic
- Difficult to model gradual information decay
- Poor support for dynamic information sources

## Consequences

### Positive

1. **Realistic Information Limits**: Agents make decisions based on limited, realistic information
2. **Differentiated Capabilities**: Different agents can have different information-gathering strengths
3. **Narrative Tension**: Unknown information creates suspense and discovery opportunities
4. **Tactical Depth**: Information becomes a strategic resource to manage
5. **Scalable Performance**: Filtering reduces information processing overhead
6. **Debuggable**: Clear rules for what agents can/cannot see
7. **Provenance Tracking**: All information includes source attribution for validation

### Negative

1. **Implementation Complexity**: Filtering logic must be carefully implemented
2. **Potential Information Starvation**: Agents might lack critical information for good decisions
3. **Performance Overhead**: Filtering calculations required for each turn
4. **Edge Case Handling**: Complex scenarios may have unclear information access rules
5. **Debugging Challenges**: Agent decisions may be hard to understand due to limited information

### Risks and Mitigation

**Risk**: Agents make poor decisions due to insufficient information  
**Mitigation**: Ensure minimum viable information is always available, provide "last known" information

**Risk**: Filtering performance becomes bottleneck  
**Mitigation**: Cache visibility calculations, optimize distance computations

**Risk**: Information inconsistencies between agents  
**Mitigation**: Deterministic filtering rules, shared state validation

## Implementation Details

### Knowledge Scope Definition
```python
class KnowledgeScope(BaseModel):
    channel: Literal["visual", "radio", "intel"]  # Information type
    range: int = Field(..., ge=0)                # Access range
```

### Filtering Algorithm
1. **Find Agent Entity**: Locate the agent in the world state
2. **Apply Channel Rules**: For each knowledge scope channel:
   - **Visual**: Entities within direct observation range
   - **Radio**: Entities with radio capability within communication range
   - **Intel**: Faction allies and intelligence network contacts
3. **Combine Visible Sets**: Union of all visible entities from all channels
4. **Filter Facts**: Include only facts that reference visible entities
5. **Generate Turn Brief**: Create personalized world view with visible slice

### Performance Optimizations
- **Caching**: Store visibility calculations for identical world states
- **Early Exit**: Skip expensive calculations when ranges are exceeded
- **Spatial Indexing**: Use spatial data structures for efficient distance queries
- **Incremental Updates**: Only recalculate visibility when relevant entities move

### Integration Points
- **Iron Laws**: Information Limit validation uses visibility results
- **Turn Brief Generation**: Core filtering happens during brief creation
- **Threat Assessment**: Only visible entities can be assessed as threats
- **Knowledge Retrieval**: KB queries consider agent's information context

## Edge Cases and Solutions

### 1. **Indirect Information**
**Problem**: Agent learns about distant entities through visible allies
**Solution**: Intel channel enables information sharing between faction members

### 2. **Information Persistence**
**Problem**: What happens to information when entities move out of range?
**Solution**: Implement "last known" information with confidence decay over time

### 3. **Communication Networks**
**Problem**: Complex multi-hop communication chains
**Solution**: Limit to direct communication only for simplicity, future enhancement possible

### 4. **Stealth and Concealment**
**Problem**: Some entities should be harder to detect
**Solution**: Entity tags can modify detection rules (future enhancement)

## Testing Strategy
- **Unit Tests**: Each channel type tested independently
- **Integration Tests**: Multi-channel scenarios
- **Performance Tests**: Large world state filtering benchmarks
- **Edge Case Tests**: Boundary conditions and unusual scenarios

## Related Decisions
- ADR-001: Iron Laws use visibility results for Information Limit validation
- ADR-004: Context Supply Chain provides world state input to filtering
- ADR-003: Pydantic schemas define KnowledgeScope structure

## Status Changes
- 2025-08-11: Proposed and accepted during initial architecture design