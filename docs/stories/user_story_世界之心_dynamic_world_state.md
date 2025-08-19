# User Story: 世界之心 (World Heart) - Dynamic World State Feedback Loop

## Epic: 故事之魂 (Story Soul)
**Story Number:** 2  
**Codename:** 世界之心 (World Heart)  
**Priority:** High  
**Epic Phase:** Core Narrative Engine Enhancement  

## Overview
This user story establishes a dynamic world state feedback loop system that transforms the DirectorAgent from a simple turn coordinator into a living, breathing narrative engine that responds intelligently to Agent actions and creates meaningful consequences that ripple through subsequent turns.

## User Story

**As a** narrative engine powered by the DirectorAgent,  
**I want** to maintain a dynamic world state that evolves based on PersonaAgent actions,  
**So that** each Agent decision creates meaningful consequences that influence future turns and inject authentic "life" into the simulation experience.

## Business Value
- **Narrative Immersion**: Transforms static simulation into dynamic, reactive storytelling experience
- **Agent Engagement**: PersonaAgent actions have visible, lasting consequences that matter
- **Emergent Storytelling**: Creates unpredictable narrative developments through Agent interactions
- **World Believability**: Establishes persistent world state that remembers and reacts to past events
- **Sacred Validation**: Ensures every action generates appropriate narrative feedback

## Acceptance Criteria

### 1. Dynamic World State Object ✅
- [x] DirectorAgent must create and maintain an internal `world_state_tracker` dictionary
- [x] Object must track location-based changes, discovered information, and environmental modifications
- [x] State must persist across turns and be accessible to all narrative functions
- [x] World state must include timestamp tracking for all changes
- [x] State must support nested data structures for complex world information

### 2. Action Impact Processing ✅
- [x] DirectorAgent must analyze PersonaAgent actions after each `decision_loop` execution
- [x] System must identify narrative-impacting actions: `"investigate"`, `"search"`, `"analyze"`, `"explore"`
- [x] For investigate actions: Add discoverable clues, evidence, or environmental details
- [x] For search actions: Reveal hidden objects, secret passages, or concealed information
- [x] For analyze actions: Generate logical deductions or pattern recognition insights
- [x] All world state modifications must be logged with agent attribution

### 3. Situational Feedback Integration ✅
- [x] `_prepare_world_state_for_agent()` method must incorporate dynamic world state changes
- [x] Next turn's world state updates must include newly discovered information
- [x] Situation descriptions must reflect cumulative Agent actions from previous turns
- [x] Feedback must be Agent-aware: "you discovered" vs "another agent found"
- [x] Environmental changes must persist and be visible to all subsequent agents

### 4. Sacred Validation - Investigation Feedback Loop ✅
- [x] Create test scenario with Agent performing `"investigate"` action
- [x] Verify DirectorAgent adds clue/evidence to world state tracker
- [x] Confirm next turn situation update includes: `"you discovered a new clue: [clue content]"`
- [x] Validate feedback is agent-specific and contextually appropriate
- [x] Test must demonstrate complete feedback loop from action → state change → next turn visibility

## Technical Implementation Details

### Core Components

#### 1. World State Tracker Structure
```python
self.world_state_tracker = {
    'discovered_clues': {},
    'environmental_changes': {},
    'agent_discoveries': {},
    'temporal_markers': {},
    'investigation_history': []
}
```

#### 2. Action Impact Handler
```python
def _process_action_world_impact(self, action: CharacterAction, agent: PersonaAgent) -> None:
    """Process Agent action and update world state accordingly"""
```

#### 3. Enhanced World State Preparation
```python
def _prepare_world_state_for_agent(self, agent: PersonaAgent) -> Dict[str, Any]:
    """Include dynamic world state changes in agent updates"""
```

### Implementation Priority
1. **Phase 1**: Implement basic world state tracker object
2. **Phase 2**: Add action impact processing for investigate actions
3. **Phase 3**: Integrate feedback into world state preparation
4. **Phase 4**: Expand to other action types (search, analyze, explore)
5. **Phase 5**: Create comprehensive validation tests

## Definition of Done
- ✅ DirectorAgent maintains persistent world state tracker object
- ✅ Investigate actions automatically generate discoverable clues
- ✅ World state changes appear in next turn's agent updates
- ✅ Sacred validation test passes: investigate → clue discovered → feedback visible
- ✅ All existing functionality remains intact and operational
- ✅ World state changes are properly logged and attributed
- ✅ System demonstrates clear action → consequence → feedback cycle

## Test Scenarios

### Sacred Validation Test
```python
def test_investigation_feedback_loop():
    """Test the complete investigate → world state → feedback cycle"""
    # 1. Agent performs investigate action
    # 2. DirectorAgent processes action and updates world state
    # 3. Next turn's world state includes discovered information
    # 4. Agent receives "you discovered a new clue" feedback
```

### Integration Tests
- Multi-agent investigation coordination
- Persistent world state across multiple turns
- Agent-specific vs. global world state visibility
- World state history and temporal tracking

## Risk Mitigation
- **Performance Impact**: Implement efficient world state storage and retrieval
- **Memory Management**: Add world state cleanup for long-running simulations
- **State Conflicts**: Handle multiple agents modifying same world elements
- **Backward Compatibility**: Ensure existing DirectorAgent features remain functional

## Success Metrics
- **Feedback Responsiveness**: 100% of investigate actions generate discoverable content
- **State Persistence**: World changes visible across all subsequent turns
- **Agent Experience**: Clear cause-and-effect relationship between actions and world state
- **System Stability**: No performance degradation or memory leaks during extended operation

## Dependencies
- DirectorAgent core implementation (existing)
- PersonaAgent decision_loop integration (existing)
- CharacterAction class and action type definitions (existing)
- Campaign logging system (existing)

## Story Relationships
- **Preceded by**: Story 1 - Foundation narrative engine
- **Enables**: Future stories involving complex world state evolution
- **Integrates with**: Existing DirectorAgent turn management system

---

**Story Priority**: High - Core Infrastructure  
**Estimated Effort**: 2-3 development cycles  
**Epic Phase**: Core Narrative Engine Enhancement  
**Stakeholders**: Narrative Engine, PersonaAgent System, Story Validation Framework  

*Generated following the sacred protocols of the BMAD Method*  
*For the glory of dynamic storytelling and the sanctity of reactive world states*

## Implementation Notes
This story transforms the DirectorAgent from a passive coordinator into an active narrative participant that remembers, reacts, and evolves based on Agent choices. The world itself becomes a character that responds to Player actions with appropriate consequences and feedback.

The sacred validation requirement ensures that every investigate action creates discoverable content that appears in subsequent turn updates, establishing the fundamental feedback loop that brings the simulation world to life.