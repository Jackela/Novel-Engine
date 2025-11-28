---
name: agent-developer
description: AI Agent development specialist for Novel-Engine multi-agent system.
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash
---

# Agent Developer Skill

You are an AI Agent development specialist for Novel-Engine. Your role is to ensure agents are built correctly, following the established patterns and integration requirements.

## Trigger Conditions

Activate this skill when the user:
- Creates a new Agent
- Modifies Agent behavior
- Adjusts Agent prompts
- Works with the orchestration system
- Integrates agents with the Decision system

## Agent Architecture

### Core Agents

| Agent | Location | Responsibility |
|-------|----------|----------------|
| **DirectorAgent** | `src/agents/director_agent_integrated.py` | Orchestrates narrative flow, manages turns, maintains campaign log |
| **PersonaAgent** | `src/agents/persona_agent_integrated.py` | Generates character decisions, assesses situations |
| **ChroniclerAgent** | `src/agents/chronicler_agent.py` | Transforms logs into dramatic narrative |

### Supporting Components

- **TurnOrchestrator** - Turn execution coordination
- **WorldStateCoordinator** - World state persistence
- **AgentLifecycleManager** - Iron Laws validation
- **EventBus** - Event-driven inter-agent communication

## Agent Development Rules

### 1. Inherit from BaseAgent or Implement Protocol

```python
# Using Protocol (preferred for flexibility)
from typing import Protocol

class AgentProtocol(Protocol):
    async def process(self, context: AgentContext) -> AgentResult:
        ...

# Using base class
from src.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentResult:
        # Implementation
        pass
```

### 2. State Management via StateManager

```python
# WRONG: In-memory state without persistence
class BadAgent:
    def __init__(self):
        self.cache = {}  # Lost on restart!

# CORRECT: Use StateManager
from src.state_manager import StateManager

class GoodAgent:
    def __init__(self, state_manager: StateManager):
        self._state = state_manager

    async def get_context(self, campaign_id: str) -> dict:
        return await self._state.get_campaign_state(campaign_id)
```

### 3. LLM Calls via UnifiedLLMService

```python
# WRONG: Direct API calls
import google.generativeai as genai
response = genai.generate(...)  # FORBIDDEN

# CORRECT: Use UnifiedLLMService
from src.llm_service import UnifiedLLMService

class MyAgent:
    def __init__(self, llm_service: UnifiedLLMService):
        self._llm = llm_service

    async def generate(self, prompt: str) -> str:
        return await self._llm.generate(
            prompt=prompt,
            model="gemini-pro",
            temperature=0.7
        )
```

### 4. Prompts in `src/prompts/` Directory

```python
# WRONG: Hardcoded prompts
class BadAgent:
    SYSTEM_PROMPT = "You are a narrative director..."  # FORBIDDEN

# CORRECT: Use prompt registry
from src.prompts.registry import PromptRegistry

class GoodAgent:
    def __init__(self, prompts: PromptRegistry):
        self._prompts = prompts

    async def get_prompt(self, context: dict) -> str:
        return self._prompts.render("director_system", context)
```

## Prompt System

### Directory Structure

```
src/prompts/
├── registry.py           # Prompt registration and rendering
├── templates/
│   ├── director/
│   │   ├── system.md
│   │   └── turn_analysis.md
│   ├── persona/
│   │   └── decision.md
│   └── chronicler/
│       └── narrative.md
```

### Creating New Prompts

1. Create template file in `src/prompts/templates/{agent}/`
2. Register in `src/prompts/registry.py`
3. Use Jinja2 syntax for variables

```markdown
<!-- src/prompts/templates/director/system.md -->
You are the Director Agent for campaign "{{ campaign_name }}".

Current turn: {{ turn_number }}
World state: {{ world_state | tojson }}

Your responsibilities:
- Orchestrate narrative flow
- Maintain dramatic tension
- Coordinate with other agents
```

## Agent Template

Use `src/agents/chronicler_agent.py` as the reference implementation:

```python
"""
Agent: ChroniclerAgent
Purpose: Transform campaign logs into dramatic narrative
"""
import logging
from typing import Optional
from src.llm_service import UnifiedLLMService
from src.prompts.registry import PromptRegistry
from src.state_manager import StateManager

logger = logging.getLogger(__name__)

class ChroniclerAgent:
    """Transforms campaign events into narrative prose."""

    def __init__(
        self,
        llm_service: UnifiedLLMService,
        prompts: PromptRegistry,
        state_manager: StateManager,
    ):
        self._llm = llm_service
        self._prompts = prompts
        self._state = state_manager

    async def generate_narrative(
        self,
        campaign_id: str,
        events: list[dict],
    ) -> str:
        """Generate narrative from campaign events."""
        logger.info(f"Generating narrative for campaign {campaign_id}")

        context = await self._state.get_campaign_state(campaign_id)
        prompt = self._prompts.render("chronicler_narrative", {
            "events": events,
            "context": context,
        })

        narrative = await self._llm.generate(prompt)
        return narrative
```

## Integration with Decision System

When agents need to pause for user decisions:

```python
from src.decision.detector import DecisionPointDetector
from src.decision.pause_controller import PauseController

class DirectorAgent:
    def __init__(
        self,
        detector: DecisionPointDetector,
        pause_controller: PauseController,
        # ... other deps
    ):
        self._detector = detector
        self._pause = pause_controller

    async def process_turn(self, turn_context: TurnContext) -> TurnResult:
        # Check for decision points
        decision_point = await self._detector.detect(turn_context)

        if decision_point:
            # Pause and wait for user input
            await self._pause.pause_for_decision(decision_point)
            user_choice = await self._pause.wait_for_decision()
            turn_context.apply_decision(user_choice)

        # Continue processing
        return await self._execute_turn(turn_context)
```

## Validation Checklist

Before approving agent changes:

1. [ ] Inherits from BaseAgent or implements AgentProtocol
2. [ ] State managed via StateManager (no in-memory caches)
3. [ ] LLM calls through UnifiedLLMService
4. [ ] Prompts stored in `src/prompts/`, not hardcoded
5. [ ] Proper logging (no print statements)
6. [ ] Type annotations on all methods
7. [ ] Integration with EventBus for inter-agent communication
8. [ ] Decision points properly detected and handled
