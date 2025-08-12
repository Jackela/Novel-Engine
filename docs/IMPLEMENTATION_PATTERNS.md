# Novel Engine Implementation Patterns

*Document Version: 1.0*  
*Last Updated: 2025-08-11*  
*Purpose: Code patterns and implementation templates for the 8 Work Orders*

## Overview

This document provides concrete code patterns, templates, and examples for implementing each of the 8 Work Orders defined in the Codex Executio. Each pattern includes complete code examples, error handling, and integration points.

## 🏗️ General Implementation Principles

### Code Style Guidelines
- **Type Hints**: Use comprehensive type annotations
- **Error Handling**: Implement explicit error handling with custom exceptions
- **Logging**: Use structured logging with context
- **Testing**: Write tests before implementation (TDD)
- **Documentation**: Document public interfaces with docstrings

### File Organization Pattern
```python
# Standard imports
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

# Third-party imports  
from pydantic import BaseModel, Field, ValidationError
from fastapi import HTTPException, status

# Local imports
from src.shared_types import WorldState, PersonaCardV2, TurnBrief
from src.engine.exceptions import AdjudicationError

# Configure logging
logger = logging.getLogger(__name__)
```

---

## 📋 PR-01: Legal & Configuration Pattern

### File Creation Pattern
```python
# Pattern: Safe file creation with content templates
from pathlib import Path
from typing import Dict, Any
import yaml

def create_legal_files() -> None:
    """Create legal and configuration files with proper content."""
    
    # 1. LEGAL.md creation
    legal_content = """# Legal Notice

This software contains no copyrighted content and is provided under fair use.

## Non-Affiliation Disclaimer
This project is not affiliated with or endorsed by any commercial entity.

## Fan Mode Compliance
When operating in 'fan' mode, users must ensure:
- Non-commercial use only
- Local distribution only
- Compliance with applicable copyright laws
"""
    
    legal_path = Path("LEGAL.md")
    legal_path.write_text(legal_content, encoding="utf-8")
    logger.info("Created LEGAL.md")
    
    # 2. NOTICE file creation
    notice_content = """Copyright Notice
This software may contain derivative content used under fair use provisions.
See LEGAL.md for full details.
"""
    
    notice_path = Path("NOTICE")
    notice_path.write_text(notice_content, encoding="utf-8")
    logger.info("Created NOTICE")
    
    # 3. settings.yaml creation with validation
    settings_data = {
        "mode": "neutral",
        "policy": {
            "monetization": "disabled",
            "provenance_required": True
        },
        "kb": {
            "enabled": True,
            "cache_size": 1000
        },
        "guard": {
            "compliance_check": True,
            "banned_terms": True
        }
    }
    
    settings_path = Path("settings.yaml")
    with open(settings_path, 'w', encoding="utf-8") as f:
        yaml.dump(settings_data, f, default_flow_style=False, indent=2)
    logger.info("Created settings.yaml")
    
    # 4. README.md disclaimer update
    disclaimer = """
## ⚖️ Legal Disclaimer

This software contains no copyrighted content and is provided for educational 
and non-commercial purposes. See LEGAL.md for complete terms.
"""
    
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        if "Legal Disclaimer" not in content:
            content = disclaimer + "\n" + content
            readme_path.write_text(content, encoding="utf-8")
            logger.info("Updated README.md with disclaimer")
```

### Test Pattern
```python
# tests/test_foundation.py
import pytest
from pathlib import Path
import yaml

def test_legal_files_exist():
    """Test that all legal files are created."""
    assert Path("LEGAL.md").exists(), "LEGAL.md must exist"
    assert Path("NOTICE").exists(), "NOTICE file must exist"
    assert Path("settings.yaml").exists(), "settings.yaml must exist"

def test_settings_yaml_structure():
    """Test that settings.yaml has required structure."""
    settings_path = Path("settings.yaml")
    assert settings_path.exists()
    
    with open(settings_path) as f:
        settings = yaml.safe_load(f)
    
    # Required top-level keys
    required_keys = ["mode", "policy", "kb", "guard"]
    for key in required_keys:
        assert key in settings, f"settings.yaml missing key: {key}"
    
    # Validate mode is valid
    valid_modes = ["neutral", "fan", "empty"]
    assert settings["mode"] in valid_modes
    
    # Validate policy structure
    assert "monetization" in settings["policy"]
    assert "provenance_required" in settings["policy"]

def test_readme_disclaimer():
    """Test that README.md contains disclaimer."""
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text()
        assert "Legal Disclaimer" in content
```

---

## 🛡️ PR-02: Startup Guards Pattern

### Compliance Checker Pattern
```python
# src/engine/guards.py
from pathlib import Path
import yaml
from typing import Dict, Any
import sys

class ComplianceError(Exception):
    """Raised when compliance checks fail."""
    pass

class StartupGuard:
    """Validates system compliance before startup."""
    
    def __init__(self, settings_path: Path = Path("settings.yaml")):
        self.settings_path = settings_path
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load and validate settings file."""
        if not self.settings_path.exists():
            raise ComplianceError(f"Settings file not found: {self.settings_path}")
        
        try:
            with open(self.settings_path) as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ComplianceError(f"Invalid YAML in settings: {e}")
    
    def check_compliance(self) -> None:
        """Main compliance check entry point."""
        mode = self.settings.get("mode", "neutral")
        
        if mode == "fan":
            self._check_fan_mode_compliance()
        elif mode == "neutral":
            self._check_neutral_mode_compliance()
        elif mode == "empty":
            pass  # No compliance checks needed
        else:
            raise ComplianceError(f"Invalid mode: {mode}")
    
    def _check_fan_mode_compliance(self) -> None:
        """Check fan mode specific compliance."""
        registry_path = Path("private/registry.yaml")
        
        if not registry_path.exists():
            raise ComplianceError(
                "Fan mode requires private/registry.yaml with compliance settings"
            )
        
        try:
            with open(registry_path) as f:
                registry = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ComplianceError(f"Invalid registry.yaml: {e}")
        
        # Check compliance section
        compliance = registry.get("compliance", {})
        
        if not compliance.get("non_commercial", False):
            raise ComplianceError(
                "Fan mode requires non_commercial: true in registry.yaml"
            )
        
        if compliance.get("distribution") != "local_only":
            raise ComplianceError(
                "Fan mode requires distribution: local_only in registry.yaml"
            )
        
        logger.info("Fan mode compliance check passed")
    
    def _check_neutral_mode_compliance(self) -> None:
        """Check neutral mode compliance."""
        # Neutral mode has no special requirements
        logger.info("Neutral mode compliance check passed")

# Integration in scripts/build_kb.py
def main() -> None:
    """Main entry point with startup guard."""
    try:
        guard = StartupGuard()
        guard.check_compliance()
    except ComplianceError as e:
        logger.error(f"Compliance check failed: {e}")
        sys.exit(1)
    
    # Continue with normal KB building
    logger.info("Building knowledge base...")
    # ... rest of implementation

# Integration in api_server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Validate compliance on startup."""
    try:
        guard = StartupGuard()
        guard.check_compliance()
    except ComplianceError as e:
        logger.error(f"Startup compliance check failed: {e}")
        raise SystemExit(1)

@app.get("/meta/policy")
async def get_policy():
    """Return current operational policy."""
    guard = StartupGuard()
    settings = guard.settings
    
    return {
        "mode": settings.get("mode", "neutral"),
        "monetization": settings.get("policy", {}).get("monetization", "disabled"),
        "provenance_required": settings.get("policy", {}).get("provenance_required", True)
    }
```

### Test Pattern
```python
# tests/test_startup_guards.py
import pytest
from pathlib import Path
import yaml
import tempfile
from src.engine.guards import StartupGuard, ComplianceError

def test_neutral_mode_compliance():
    """Test that neutral mode passes compliance."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        settings = {"mode": "neutral", "policy": {"monetization": "disabled"}}
        yaml.dump(settings, f)
        f.flush()
        
        guard = StartupGuard(Path(f.name))
        guard.check_compliance()  # Should not raise

def test_fan_mode_requires_registry():
    """Test that fan mode fails without registry."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        settings = {"mode": "fan"}
        yaml.dump(settings, f)
        f.flush()
        
        guard = StartupGuard(Path(f.name))
        with pytest.raises(ComplianceError, match="registry.yaml"):
            guard.check_compliance()

def test_fan_mode_compliance_success():
    """Test successful fan mode compliance."""
    # Create temporary registry
    registry_dir = Path("private")
    registry_dir.mkdir(exist_ok=True)
    registry_file = registry_dir / "registry.yaml"
    
    registry_data = {
        "sources": [],
        "compliance": {
            "non_commercial": True,
            "distribution": "local_only"
        }
    }
    
    with open(registry_file, 'w') as f:
        yaml.dump(registry_data, f)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        settings = {"mode": "fan"}
        yaml.dump(settings, f)
        f.flush()
        
        guard = StartupGuard(Path(f.name))
        guard.check_compliance()  # Should not raise
    
    # Cleanup
    registry_file.unlink()
    if registry_dir.exists():
        registry_dir.rmdir()
```

---

## 🔧 PR-03: Pydantic Schemas Pattern

### Schema Definition Pattern
```python
# src/shared_types.py - Complete implementation
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field, constr, ValidationError

# Core building blocks
class Doctrine(BaseModel):
    """Doctrinal rule from knowledge base."""
    rule: constr(min_length=1)
    source_id: str

class Belief(BaseModel):
    """Core belief with weighted confidence."""
    proposition: str
    weight: float = Field(..., ge=0, le=1)

class Trait(BaseModel):
    """Personality trait with intensity."""
    name: str
    weight: float = Field(..., ge=0, le=1)

class KnowledgeScope(BaseModel):
    """Defines agent's perception capabilities."""
    channel: Literal["visual", "radio", "intel"]
    range: int = Field(..., ge=0)

class PersonaCardV2(BaseModel):
    """The digital soul of an agent."""
    id: constr(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    faction: constr(min_length=1)
    doctrine: List[Doctrine] = []
    beliefs: List[Belief] = Field(..., min_length=1)
    traits: List[Trait] = []
    knowledge_scope: List[KnowledgeScope] = Field(..., min_length=1)
    taboos: List[str] = []

# World representation
class Entity(BaseModel):
    """Any object, character, or location in the world."""
    id: str
    type: str
    name: Optional[str] = None
    pos: Optional[str] = None
    tags: List[str] = []
    assets: Optional[Dict[str, Any]] = None

class Relation(BaseModel):
    """Relationship between entities."""
    src: str
    rel: str
    dst: str

class Fact(BaseModel):
    """World fact with provenance."""
    id: str
    text: str
    confidence: float = Field(..., ge=0, le=1)
    source_id: str

class WorldRule(BaseModel):
    """Physical or canonical law."""
    name: str
    expr: str

class WorldState(BaseModel):
    """Complete objective world state."""
    turn: int = Field(..., ge=0)
    time: Optional[str] = None
    entities: List[Entity]
    relations: List[Relation] = []
    facts: List[Fact]
    rules: List[WorldRule]

# Agent interaction
class Threat(BaseModel):
    """Perceived threat assessment."""
    id: str
    distance: Literal["close", "medium", "far"]

class DoctrineSnippet(BaseModel):
    """Retrieved knowledge with provenance."""
    text: str
    source_id: str

class TurnBrief(BaseModel):
    """Subjective 'fog of war' reality for an agent."""
    for_persona: constr(min_length=1)
    visible_slice: List[str]  # Entity/fact IDs visible to agent
    threats: List[Threat] = []
    last_actions_summary: Optional[str] = None
    doctrine_snippets: List[DoctrineSnippet] = Field(..., max_length=8)

# Action system
class ExpectedEffect(BaseModel):
    """Anticipated action outcome."""
    fact: str
    delta: float

class DoctrineCheck(BaseModel):
    """Doctrine compliance validation."""
    violations: List[str] = []
    notes: Optional[str] = None

class CharacterAction(BaseModel):
    """Structured agent decision."""
    action_type: Literal["move", "attack", "parley", "regroup", "scan", "observe"]
    target: Optional[str] = None
    intent: constr(min_length=1, max_length=256)
    justification: constr(min_length=1, max_length=512)
    expected_effects: List[ExpectedEffect] = []
    doctrine_check: Optional[DoctrineCheck] = None
    confidence: float = Field(..., ge=0, le=1)

# Chronicle system
class Paragraph(BaseModel):
    """Chronicle paragraph with citations."""
    text: str
    citations: List[str]  # source_id references

class ChronicleSection(BaseModel):
    """Chronicle section with paragraphs."""
    heading: Optional[str] = None
    paragraphs: List[Paragraph] = Field(..., min_length=1)

class ChronicleSpec(BaseModel):
    """Complete narrative chronicle."""
    sections: List[ChronicleSection] = Field(..., min_length=1)

# Knowledge base
class CanonSource(BaseModel):
    """Knowledge base source document."""
    id: str
    title: str
    version: str
    license: str
    kind: Literal["text", "pdf", "image"]
    path: str
    chunks: Literal["auto", "fixed"]
    hash: str

class CanonCompliance(BaseModel):
    """Legal compliance settings."""
    non_commercial: bool
    distribution: Literal["local_only", "restricted"]

class CanonRegistry(BaseModel):
    """Knowledge base manifest."""
    sources: List[CanonSource] = Field(..., min_length=1)
    compliance: Optional[CanonCompliance] = None
```

### FastAPI Integration Pattern
```python
# api_server.py - Updated endpoints with Pydantic validation
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List
from src.shared_types import (
    PersonaCardV2, CharacterAction, WorldState, 
    ChronicleSpec, TurnBrief
)

app = FastAPI()

@app.post("/simulations/run", status_code=202)
async def run_simulation(request: dict):
    """Start simulation with validation."""
    try:
        # Validate request structure
        seed_id = request["seed_id"]
        steps = request["steps"]
        
        if not isinstance(seed_id, str) or len(seed_id.strip()) == 0:
            raise HTTPException(
                status_code=400, 
                detail="seed_id must be non-empty string"
            )
        
        if not isinstance(steps, int) or steps < 1:
            raise HTTPException(
                status_code=400,
                detail="steps must be positive integer"
            )
        
        # Generate run ID and start simulation
        run_id = f"run_{hash(seed_id)}_{steps}"
        # ... simulation logic
        
        return {"run_id": run_id}
        
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required field: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/simulations/{run_id}/turn")
async def execute_turn(
    run_id: str, 
    actions: List[CharacterAction]
) -> dict:
    """Execute turn with Pydantic validation."""
    try:
        # Actions automatically validated by Pydantic
        logger.info(f"Processing {len(actions)} actions for run {run_id}")
        
        # Process each action
        world_state = WorldState(
            turn=1,
            entities=[],
            facts=[],
            rules=[]
        )
        
        # ... action processing logic
        
        return {
            "world": world_state.dict(),
            "log_id": f"log_{run_id}_turn_1"
        }
        
    except ValidationError as e:
        # Pydantic validation failed
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Turn execution failed: {str(e)}"
        )

@app.get("/characters")
async def list_characters() -> List[PersonaCardV2]:
    """List available personas."""
    # Return validated PersonaCardV2 objects
    personas = [
        PersonaCardV2(
            id="test_persona",
            faction="neutral",
            beliefs=[
                {"proposition": "Truth is important", "weight": 0.9}
            ],
            knowledge_scope=[
                {"channel": "visual", "range": 10}
            ]
        )
    ]
    return personas

@app.post("/chronicle")
async def generate_chronicle(request: dict) -> ChronicleSpec:
    """Generate narrative chronicle."""
    try:
        run_id = request["run_id"]
        # ... chronicle generation logic
        
        chronicle = ChronicleSpec(
            sections=[
                {
                    "heading": "Chapter 1",
                    "paragraphs": [
                        {
                            "text": "The story begins...",
                            "citations": ["source_1"]
                        }
                    ]
                }
            ]
        )
        return chronicle
        
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail="Missing run_id in request"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chronicle generation failed: {str(e)}"
        )

# Error handling for Pydantic validation
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )
```

### Test Pattern
```python
# tests/test_schemas.py
import pytest
from pydantic import ValidationError
from src.shared_types import PersonaCardV2, CharacterAction, WorldState

def test_persona_card_valid():
    """Test valid PersonaCardV2 creation."""
    persona = PersonaCardV2(
        id="test_agent",
        faction="rebels",
        beliefs=[{"proposition": "Freedom is essential", "weight": 0.9}],
        knowledge_scope=[{"channel": "visual", "range": 5}]
    )
    assert persona.id == "test_agent"
    assert len(persona.beliefs) == 1
    assert persona.beliefs[0].weight == 0.9

def test_persona_card_invalid_id():
    """Test PersonaCardV2 with invalid ID format."""
    with pytest.raises(ValidationError) as exc_info:
        PersonaCardV2(
            id="invalid id with spaces",  # Should fail regex pattern
            faction="rebels",
            beliefs=[{"proposition": "Test", "weight": 0.5}],
            knowledge_scope=[{"channel": "visual", "range": 1}]
        )
    
    errors = exc_info.value.errors()
    assert any("pattern" in error["type"] for error in errors)

def test_character_action_valid():
    """Test valid CharacterAction creation."""
    action = CharacterAction(
        action_type="move",
        target="location_1",
        intent="Move to safer position",
        justification="Current position is exposed to enemy fire",
        confidence=0.8
    )
    assert action.action_type == "move"
    assert action.confidence == 0.8

def test_character_action_intent_too_long():
    """Test CharacterAction with intent exceeding max length."""
    long_intent = "a" * 300  # Exceeds 256 char limit
    
    with pytest.raises(ValidationError) as exc_info:
        CharacterAction(
            action_type="scan",
            intent=long_intent,
            justification="Valid justification",
            confidence=0.7
        )
    
    errors = exc_info.value.errors()
    assert any("max_length" in error["type"] for error in errors)

def test_world_state_turn_negative():
    """Test WorldState with negative turn number."""
    with pytest.raises(ValidationError) as exc_info:
        WorldState(
            turn=-1,  # Should fail ge=0 constraint
            entities=[],
            facts=[],
            rules=[]
        )
    
    errors = exc_info.value.errors()
    assert any("greater_than_equal" in error["type"] for error in errors)
```

---

## 🔍 PR-04: IP Sanitization Pattern

### Term Guardian Pattern
```python
# scripts/term_guard.py
import re
from pathlib import Path
from typing import List, Dict, Tuple
import sys
import argparse

class TermGuard:
    """Scans codebase for banned intellectual property terms."""
    
    # Banned terms mapping to neutral replacements
    BANNED_TERMS = {
        # Example mappings - actual terms would be project-specific
        "ProprietaryTerm": "GenericTerm",
        "CopyrightedName": "CharacterName",
        "TrademarkName": "FactionName",
    }
    
    # File patterns to scan
    SCAN_PATTERNS = [
        "**/*.py",
        "**/*.md", 
        "**/*.yaml",
        "**/*.json",
        "**/*.txt"
    ]
    
    # Directories to skip
    SKIP_DIRS = {
        ".git", "__pycache__", ".pytest_cache", 
        "node_modules", ".venv", "venv"
    }
    
    def __init__(self, root_dir: Path = Path(".")):
        self.root_dir = root_dir
        self.violations: List[Tuple[Path, int, str, str]] = []
    
    def scan_files(self) -> List[Tuple[Path, int, str, str]]:
        """Scan all files for banned terms."""
        self.violations.clear()
        
        for pattern in self.SCAN_PATTERNS:
            for file_path in self.root_dir.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                
                self._scan_file(file_path)
        
        return self.violations
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Skip if in banned directory
        for part in file_path.parts:
            if part in self.SKIP_DIRS:
                return True
        
        # Skip binary files
        if file_path.suffix in {'.pyc', '.pyo', '.so', '.dll', '.exe'}:
            return True
        
        return False
    
    def _scan_file(self, file_path: Path) -> None:
        """Scan individual file for banned terms."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for banned_term, replacement in self.BANNED_TERMS.items():
                    if banned_term.lower() in line.lower():
                        self.violations.append((
                            file_path, 
                            line_num, 
                            banned_term, 
                            line.strip()
                        ))
                        
        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")
    
    def replace_terms(self, dry_run: bool = True) -> Dict[str, int]:
        """Replace banned terms with neutral alternatives."""
        replacement_count = {}
        
        for violation in self.violations:
            file_path, line_num, banned_term, _ = violation
            
            if banned_term not in replacement_count:
                replacement_count[banned_term] = 0
            
            if not dry_run:
                self._replace_in_file(file_path, banned_term)
            
            replacement_count[banned_term] += 1
        
        return replacement_count
    
    def _replace_in_file(self, file_path: Path, banned_term: str) -> None:
        """Replace term in specific file."""
        replacement = self.BANNED_TERMS[banned_term]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Case-insensitive replacement while preserving case
            def replace_preserve_case(match):
                original = match.group()
                if original.isupper():
                    return replacement.upper()
                elif original.islower():
                    return replacement.lower()
                elif original.istitle():
                    return replacement.title()
                return replacement
            
            pattern = re.compile(re.escape(banned_term), re.IGNORECASE)
            new_content = pattern.sub(replace_preserve_case, content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
        except Exception as e:
            print(f"Error replacing terms in {file_path}: {e}")
    
    def generate_report(self) -> str:
        """Generate scan report."""
        if not self.violations:
            return "✅ No banned terms found!"
        
        report = [f"❌ Found {len(self.violations)} violations:\n"]
        
        grouped = {}
        for file_path, line_num, banned_term, line_content in self.violations:
            key = str(file_path)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append((line_num, banned_term, line_content))
        
        for file_path, violations in grouped.items():
            report.append(f"📁 {file_path}:")
            for line_num, banned_term, line_content in violations:
                report.append(f"   Line {line_num}: '{banned_term}' in: {line_content[:80]}...")
            report.append("")
        
        return "\n".join(report)

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Scan for banned IP terms")
    parser.add_argument("--fix", action="store_true", help="Fix violations automatically")
    parser.add_argument("--root", type=Path, default=Path("."), help="Root directory to scan")
    
    args = parser.parse_args()
    
    guard = TermGuard(args.root)
    violations = guard.scan_files()
    
    print(guard.generate_report())
    
    if violations:
        if args.fix:
            replacements = guard.replace_terms(dry_run=False)
            print(f"✅ Fixed {sum(replacements.values())} violations")
            return 0
        else:
            print("Run with --fix to automatically replace terms")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### CI Integration Pattern
```yaml
# .github/workflows/ip-guard.yml
name: IP Term Guard

on: [push, pull_request]

jobs:
  ip-guard:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Run IP term scan
      run: |
        python scripts/term_guard.py
        if [ $? -ne 0 ]; then
          echo "❌ Banned terms found! See output above."
          exit 1
        fi
        echo "✅ IP scan passed"
```

---

## 🔍 PR-05: TurnBrief Generator Pattern

### Fog of War Implementation Pattern
```python
# src/engine/director.py - _build_turn_brief implementation
from typing import List, Set
import logging
from src.shared_types import WorldState, PersonaCardV2, TurnBrief, DoctrineSnippet
from src.engine.kb import KnowledgeBase

logger = logging.getLogger(__name__)

class DirectorAgent:
    """Orchestrates simulation and builds turn briefs."""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self._entity_visibility_cache = {}
    
    def _build_turn_brief(
        self, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> TurnBrief:
        """Build personalized turn brief with Fog of War filtering."""
        
        # 1. Apply Fog of War filtering
        visible_entities = self._apply_fog_of_war(world_state, persona)
        visible_facts = self._filter_facts_by_visibility(world_state, visible_entities)
        
        # 2. Assess threats
        threats = self._assess_threats(world_state, persona, visible_entities)
        
        # 3. Retrieve relevant knowledge
        doctrine_snippets = self._retrieve_knowledge(world_state, persona)
        
        # 4. Build visible slice (entity + fact IDs)
        visible_slice = list(visible_entities) + [f.id for f in visible_facts]
        
        # 5. Generate last actions summary (if applicable)
        last_actions = self._get_last_actions_summary(world_state, persona)
        
        return TurnBrief(
            for_persona=persona.id,
            visible_slice=visible_slice,
            threats=threats,
            last_actions_summary=last_actions,
            doctrine_snippets=doctrine_snippets
        )
    
    def _apply_fog_of_war(
        self, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> Set[str]:
        """Apply Fog of War filtering based on knowledge scope."""
        visible_entities = set()
        
        # Find the persona's entity in world state
        persona_entity = None
        for entity in world_state.entities:
            if entity.id == persona.id:
                persona_entity = entity
                break
        
        if not persona_entity:
            logger.warning(f"Persona {persona.id} not found in world state")
            return visible_entities
        
        # Apply visibility rules for each knowledge scope
        for scope in persona.knowledge_scope:
            if scope.channel == "visual":
                visible_entities.update(
                    self._get_visually_accessible(
                        world_state, persona_entity, scope.range
                    )
                )
            elif scope.channel == "radio":
                visible_entities.update(
                    self._get_radio_accessible(
                        world_state, persona_entity, scope.range
                    )
                )
            elif scope.channel == "intel":
                visible_entities.update(
                    self._get_intel_accessible(
                        world_state, persona_entity, scope.range
                    )
                )
        
        # Always include self
        visible_entities.add(persona.id)
        
        logger.debug(f"Persona {persona.id} can see {len(visible_entities)} entities")
        return visible_entities
    
    def _get_visually_accessible(
        self, 
        world_state: WorldState, 
        observer: Entity, 
        range_limit: int
    ) -> Set[str]:
        """Get entities visible through direct observation."""
        visible = set()
        
        for entity in world_state.entities:
            if entity.id == observer.id:
                continue
            
            # Simple distance-based visibility (can be enhanced)
            distance = self._calculate_distance(observer, entity)
            if distance <= range_limit:
                visible.add(entity.id)
        
        return visible
    
    def _get_radio_accessible(
        self, 
        world_state: WorldState, 
        observer: Entity, 
        range_limit: int
    ) -> Set[str]:
        """Get entities accessible through radio communication."""
        # Implementation depends on specific communication rules
        accessible = set()
        
        # Example: entities with radio capability within range
        for entity in world_state.entities:
            if "radio" in entity.tags:
                distance = self._calculate_distance(observer, entity)
                if distance <= range_limit:
                    accessible.add(entity.id)
        
        return accessible
    
    def _get_intel_accessible(
        self, 
        world_state: WorldState, 
        observer: Entity, 
        range_limit: int
    ) -> Set[str]:
        """Get entities accessible through intelligence gathering."""
        # Intelligence might provide broader awareness
        accessible = set()
        
        # Example: faction allies share intelligence
        observer_faction = getattr(observer, 'faction', None)
        
        for entity in world_state.entities:
            if hasattr(entity, 'faction') and entity.faction == observer_faction:
                accessible.add(entity.id)
        
        return accessible
    
    def _calculate_distance(self, entity1: Entity, entity2: Entity) -> int:
        """Calculate distance between entities."""
        # Simplified distance calculation
        # Real implementation would parse position coordinates
        if not entity1.pos or not entity2.pos:
            return 999  # Unknown positions are "far"
        
        # Simple grid-based distance
        try:
            x1, y1 = map(int, entity1.pos.split(','))
            x2, y2 = map(int, entity2.pos.split(','))
            return abs(x1 - x2) + abs(y1 - y2)  # Manhattan distance
        except (ValueError, AttributeError):
            return 999
    
    def _filter_facts_by_visibility(
        self, 
        world_state: WorldState, 
        visible_entities: Set[str]
    ) -> List[Fact]:
        """Filter facts to only those about visible entities."""
        visible_facts = []
        
        for fact in world_state.facts:
            # Check if fact mentions any visible entity
            fact_mentions_visible = any(
                entity_id in fact.text 
                for entity_id in visible_entities
            )
            
            if fact_mentions_visible:
                visible_facts.append(fact)
        
        return visible_facts
    
    def _assess_threats(
        self, 
        world_state: WorldState, 
        persona: PersonaCardV2, 
        visible_entities: Set[str]
    ) -> List[Threat]:
        """Assess threats based on visible entities and relationships."""
        threats = []
        
        # Find hostile relationships
        for relation in world_state.relations:
            if (relation.src == persona.id and 
                relation.rel in ["hostile_to", "enemy_of"] and
                relation.dst in visible_entities):
                
                # Determine threat distance
                distance = self._get_threat_distance(
                    world_state, persona.id, relation.dst
                )
                
                threats.append(Threat(
                    id=relation.dst,
                    distance=distance
                ))
        
        return threats
    
    def _get_threat_distance(
        self, 
        world_state: WorldState, 
        observer_id: str, 
        threat_id: str
    ) -> str:
        """Categorize threat distance."""
        observer = next(e for e in world_state.entities if e.id == observer_id)
        threat = next(e for e in world_state.entities if e.id == threat_id)
        
        distance = self._calculate_distance(observer, threat)
        
        if distance <= 2:
            return "close"
        elif distance <= 5:
            return "medium"
        else:
            return "far"
    
    def _retrieve_knowledge(
        self, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> List[DoctrineSnippet]:
        """Retrieve relevant knowledge from knowledge base."""
        # Build query from current context
        query_terms = []
        
        # Add faction-specific terms
        query_terms.append(persona.faction)
        
        # Add current situation terms
        for entity in world_state.entities[:5]:  # Top 5 entities
            if entity.name:
                query_terms.append(entity.name)
        
        query = " ".join(query_terms)
        
        # Retrieve from knowledge base (max 8 snippets as per schema)
        snippets = self.kb.retrieve(query, top_k=8)
        
        return snippets
    
    def _get_last_actions_summary(
        self, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> Optional[str]:
        """Generate summary of last actions taken."""
        # This would typically come from the campaign log
        # For now, return None (indicating no previous actions)
        return None
```

### Test Pattern
```python
# tests/test_director_agent.py
import pytest
from src.engine.director import DirectorAgent
from src.engine.kb import MockKnowledgeBase
from src.shared_types import WorldState, PersonaCardV2, Entity, KnowledgeScope

@pytest.fixture
def mock_kb():
    """Mock knowledge base for testing."""
    return MockKnowledgeBase()

@pytest.fixture 
def director(mock_kb):
    """Director agent with mock KB."""
    return DirectorAgent(mock_kb)

@pytest.fixture
def sample_world_state():
    """Sample world state for testing."""
    return WorldState(
        turn=1,
        entities=[
            Entity(id="agent_1", type="character", pos="0,0"),
            Entity(id="enemy_1", type="character", pos="1,1"), 
            Entity(id="distant_entity", type="object", pos="10,10"),
            Entity(id="ally_1", type="character", pos="0,1", tags=["radio"])
        ],
        facts=[
            {
                "id": "fact_1",
                "text": "agent_1 is positioned defensively", 
                "confidence": 0.9,
                "source_id": "observation"
            }
        ],
        rules=[]
    )

@pytest.fixture
def test_persona():
    """Test persona with limited visual scope."""
    return PersonaCardV2(
        id="agent_1",
        faction="rebels",
        beliefs=[{"proposition": "Freedom matters", "weight": 0.8}],
        knowledge_scope=[
            KnowledgeScope(channel="visual", range=3)
        ]
    )

def test_fog_of_war_masking(director, sample_world_state, test_persona):
    """Test that distant entities are masked by Fog of War."""
    turn_brief = director._build_turn_brief(sample_world_state, test_persona)
    
    # Should see self and nearby entities, but not distant ones
    assert "agent_1" in turn_brief.visible_slice  # Self
    assert "enemy_1" in turn_brief.visible_slice  # Within range (distance 2)
    assert "ally_1" in turn_brief.visible_slice   # Within range (distance 1)
    assert "distant_entity" not in turn_brief.visible_slice  # Out of range

def test_doctrine_snippets_injection(director, sample_world_state, test_persona, mock_kb):
    """Test that knowledge base snippets are injected."""
    # Configure mock KB to return test snippets
    mock_kb.set_response([
        {"text": "Rebel tactics emphasize mobility", "source_id": "manual_1"},
        {"text": "Avoid direct confrontation", "source_id": "manual_2"}
    ])
    
    turn_brief = director._build_turn_brief(sample_world_state, test_persona)
    
    assert len(turn_brief.doctrine_snippets) == 2
    assert turn_brief.doctrine_snippets[0].text == "Rebel tactics emphasize mobility"
    assert turn_brief.doctrine_snippets[0].source_id == "manual_1"

def test_threat_assessment(director, sample_world_state, test_persona):
    """Test threat detection and distance categorization."""
    # Add hostile relationship
    sample_world_state.relations.append({
        "src": "agent_1",
        "rel": "hostile_to", 
        "dst": "enemy_1"
    })
    
    turn_brief = director._build_turn_brief(sample_world_state, test_persona)
    
    assert len(turn_brief.threats) == 1
    assert turn_brief.threats[0].id == "enemy_1"
    assert turn_brief.threats[0].distance == "close"  # Distance 2 is "close"

def test_multi_channel_knowledge_scope(director, sample_world_state):
    """Test persona with multiple knowledge channels."""
    multi_scope_persona = PersonaCardV2(
        id="agent_1",
        faction="rebels", 
        beliefs=[{"proposition": "Test", "weight": 0.5}],
        knowledge_scope=[
            KnowledgeScope(channel="visual", range=2),
            KnowledgeScope(channel="radio", range=5)
        ]
    )
    
    turn_brief = director._build_turn_brief(sample_world_state, multi_scope_persona)
    
    # Should see both visually accessible and radio accessible entities
    assert "ally_1" in turn_brief.visible_slice  # Has radio tag, within radio range
```

---

## 🛡️ PR-06: Iron Adjudicator Pattern

### Action Validation Pattern
```python
# src/engine/director.py - _adjudicate_action implementation
from typing import Dict, Any, Optional
from src.shared_types import CharacterAction, WorldState, PersonaCardV2
from src.engine.exceptions import AdjudicationError

class AdjudicationError(Exception):
    """Raised when action violates Iron Laws."""
    
    def __init__(self, code: str, message: str, action: Optional[CharacterAction] = None):
        self.code = code
        self.message = message
        self.action = action
        super().__init__(f"{code}: {message}")

class DirectorAgent:
    """Extended with adjudication capabilities."""
    
    def _adjudicate_action(
        self, 
        action: CharacterAction, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> bool:
        """Validate action against the 5 Iron Laws."""
        
        try:
            # Iron Law 1: Resource Conservation
            self._validate_resource_conservation(action, world_state, persona)
            
            # Iron Law 2: Information Limit  
            self._validate_information_limit(action, world_state, persona)
            
            # Iron Law 3: State Consistency
            self._validate_state_consistency(action, world_state, persona)
            
            # Iron Law 4: Rule Adherence
            self._validate_rule_adherence(action, world_state)
            
            # Iron Law 5: Canon Preservation
            self._validate_canon_preservation(action, world_state)
            
            logger.info(f"Action {action.action_type} for {persona.id} passed adjudication")
            return True
            
        except AdjudicationError as e:
            logger.warning(f"Action rejected: {e}")
            # Attempt repair if possible
            repaired_action = self._repair_action(action, world_state, persona, e)
            if repaired_action:
                return self._adjudicate_action(repaired_action, world_state, persona)
            else:
                raise e
    
    def _validate_resource_conservation(
        self, 
        action: CharacterAction, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> None:
        """Iron Law 1: Actions cannot result in negative resource values."""
        
        # Find persona entity
        persona_entity = self._find_entity(world_state, persona.id)
        if not persona_entity:
            raise AdjudicationError(
                "E001_RESOURCE_NEGATIVE",
                f"Persona entity {persona.id} not found in world state"
            )
        
        # Check resource implications of action
        if action.action_type == "attack":
            # Attacking consumes energy/ammo
            current_energy = persona_entity.assets.get("energy", 0) if persona_entity.assets else 0
            energy_cost = 10  # Attack costs 10 energy
            
            if current_energy - energy_cost < 0:
                raise AdjudicationError(
                    "E001_RESOURCE_NEGATIVE",
                    f"Attack would reduce energy to {current_energy - energy_cost} (minimum: 0)",
                    action
                )
        
        elif action.action_type == "move":
            # Movement consumes energy
            current_energy = persona_entity.assets.get("energy", 0) if persona_entity.assets else 0
            move_cost = 5
            
            if current_energy - move_cost < 0:
                raise AdjudicationError(
                    "E001_RESOURCE_NEGATIVE", 
                    f"Move would reduce energy to {current_energy - move_cost} (minimum: 0)",
                    action
                )
    
    def _validate_information_limit(
        self, 
        action: CharacterAction, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> None:
        """Iron Law 2: Actions can only target entities visible to the actor."""
        
        if not action.target:
            return  # No target to validate
        
        # Build visibility set for this persona
        visible_entities = self._apply_fog_of_war(world_state, persona)
        
        if action.target not in visible_entities:
            raise AdjudicationError(
                "E002_TARGET_INVALID",
                f"Action targets {action.target} which is not visible to {persona.id}",
                action
            )
    
    def _validate_state_consistency(
        self, 
        action: CharacterAction, 
        world_state: WorldState, 
        persona: PersonaCardV2
    ) -> None:
        """Iron Law 3: Actions must be permitted for current entity state."""
        
        persona_entity = self._find_entity(world_state, persona.id)
        if not persona_entity:
            raise AdjudicationError(
                "E003_ACTION_IMPOSSIBLE",
                f"Persona entity {persona.id} not found"
            )
        
        # Check state-dependent action restrictions
        entity_state = persona_entity.assets.get("state", "active") if persona_entity.assets else "active"
        
        if entity_state == "incapacitated":
            # Incapacitated entities can only observe
            if action.action_type not in ["observe", "scan"]:
                raise AdjudicationError(
                    "E003_ACTION_IMPOSSIBLE",
                    f"Entity {persona.id} is incapacitated and cannot {action.action_type}",
                    action
                )
        
        elif entity_state == "hidden":
            # Hidden entities lose stealth if they attack
            if action.action_type == "attack":
                # This is allowed but has consequences (breaking stealth)
                pass
        
        # Check equipment requirements
        if action.action_type == "attack":
            has_weapon = persona_entity.assets.get("weapon") if persona_entity.assets else False
            if not has_weapon:
                raise AdjudicationError(
                    "E003_ACTION_IMPOSSIBLE",
                    f"Entity {persona.id} has no weapon for attack action",
                    action
                )
    
    def _validate_rule_adherence(
        self, 
        action: CharacterAction, 
        world_state: WorldState
    ) -> None:
        """Iron Law 4: Actions cannot contradict established world rules."""
        
        for rule in world_state.rules:
            if not self._check_rule_compliance(action, rule):
                raise AdjudicationError(
                    "E004_LOGIC_VIOLATION",
                    f"Action violates world rule: {rule.name}",
                    action
                )
    
    def _check_rule_compliance(self, action: CharacterAction, rule: WorldRule) -> bool:
        """Check if action complies with a specific world rule."""
        
        # Simple rule evaluation (can be enhanced with proper parser)
        if rule.name == "no_flight":
            # Rule: entities cannot fly
            if action.action_type == "move" and "fly" in action.intent.lower():
                return False
        
        elif rule.name == "daylight_only":
            # Rule: certain actions only allowed during day
            if action.action_type in ["scan", "observe"] and "night" in rule.expr:
                return False
        
        return True
    
    def _validate_canon_preservation(
        self, 
        action: CharacterAction, 
        world_state: WorldState
    ) -> None:
        """Iron Law 5: Actions cannot violate canonical source material."""
        
        # Check for canon violations in action content
        if self._contains_canon_violation(action):
            raise AdjudicationError(
                "E005_CANON_BREACH",
                f"Action violates canonical source constraints",
                action
            )
    
    def _contains_canon_violation(self, action: CharacterAction) -> bool:
        """Check if action violates canonical constraints."""
        
        # Example checks (would be customized per project)
        canon_violations = [
            "impossible_technology",
            "character_resurrection", 
            "timeline_paradox"
        ]
        
        action_text = f"{action.intent} {action.justification}".lower()
        
        return any(violation in action_text for violation in canon_violations)
    
    def _repair_action(
        self, 
        action: CharacterAction, 
        world_state: WorldState, 
        persona: PersonaCardV2,
        error: AdjudicationError
    ) -> Optional[CharacterAction]:
        """Attempt to repair a failed action."""
        
        if error.code == "E001_RESOURCE_NEGATIVE":
            # Try to reduce action intensity
            if action.action_type == "attack":
                # Suggest weaker attack
                return CharacterAction(
                    action_type="scan",  # Fallback to safer action
                    target=action.target,
                    intent="Assess target before engaging",
                    justification="Insufficient resources for direct attack",
                    confidence=action.confidence * 0.7
                )
        
        elif error.code == "E002_TARGET_INVALID":
            # Try to target a visible entity instead
            visible_entities = self._apply_fog_of_war(world_state, persona)
            if visible_entities:
                alternative_target = next(iter(visible_entities - {persona.id}), None)
                if alternative_target:
                    return CharacterAction(
                        action_type=action.action_type,
                        target=alternative_target,
                        intent=f"Redirect action to visible target",
                        justification="Original target not visible, engaging alternative",
                        confidence=action.confidence * 0.5
                    )
        
        elif error.code == "E003_ACTION_IMPOSSIBLE":
            # Fallback to basic observe action
            return CharacterAction(
                action_type="observe",
                target=None,
                intent="Assess current situation",
                justification="Unable to perform intended action due to state constraints", 
                confidence=0.3
            )
        
        # No repair possible
        return None
    
    def _find_entity(self, world_state: WorldState, entity_id: str) -> Optional[Entity]:
        """Find entity by ID in world state."""
        for entity in world_state.entities:
            if entity.id == entity_id:
                return entity
        return None
```

### Test Pattern
```python
# tests/test_director_agent.py - Adjudication tests
import pytest
from src.engine.director import DirectorAgent, AdjudicationError
from src.shared_types import CharacterAction, WorldState, PersonaCardV2, Entity

def test_iron_law_1_resource_negative(director, sample_world_state, test_persona):
    """Test Iron Law 1: Resource conservation."""
    
    # Set persona entity with low energy
    persona_entity = Entity(
        id="agent_1",
        type="character", 
        pos="0,0",
        assets={"energy": 5}  # Low energy
    )
    sample_world_state.entities[0] = persona_entity
    
    # Try attack that would consume more energy than available
    action = CharacterAction(
        action_type="attack",
        target="enemy_1", 
        intent="Full power attack",
        justification="Eliminate threat",
        confidence=0.9
    )
    
    with pytest.raises(AdjudicationError) as exc_info:
        director._adjudicate_action(action, sample_world_state, test_persona)
    
    assert exc_info.value.code == "E001_RESOURCE_NEGATIVE"

def test_iron_law_2_target_invalid(director, sample_world_state, test_persona):
    """Test Iron Law 2: Information limit."""
    
    # Try to target entity outside visibility range
    action = CharacterAction(
        action_type="attack",
        target="distant_entity",  # Out of visual range 
        intent="Attack distant target",
        justification="Eliminate threat",
        confidence=0.8
    )
    
    with pytest.raises(AdjudicationError) as exc_info:
        director._adjudicate_action(action, sample_world_state, test_persona)
    
    assert exc_info.value.code == "E002_TARGET_INVALID"

def test_iron_law_3_action_impossible(director, sample_world_state, test_persona):
    """Test Iron Law 3: State consistency."""
    
    # Set persona as incapacitated
    persona_entity = Entity(
        id="agent_1",
        type="character",
        pos="0,0", 
        assets={"state": "incapacitated"}
    )
    sample_world_state.entities[0] = persona_entity
    
    # Try to attack while incapacitated
    action = CharacterAction(
        action_type="attack",
        target="enemy_1",
        intent="Attack while down",
        justification="Must fight",
        confidence=0.5
    )
    
    with pytest.raises(AdjudicationError) as exc_info:
        director._adjudicate_action(action, sample_world_state, test_persona)
    
    assert exc_info.value.code == "E003_ACTION_IMPOSSIBLE"

def test_iron_law_4_logic_violation(director, sample_world_state, test_persona):
    """Test Iron Law 4: Rule adherence."""
    
    # Add world rule preventing flight
    sample_world_state.rules.append({
        "name": "no_flight",
        "expr": "entities cannot fly"
    })
    
    action = CharacterAction(
        action_type="move",
        target=None,
        intent="Fly to high ground", 
        justification="Need aerial advantage",
        confidence=0.7
    )
    
    with pytest.raises(AdjudicationError) as exc_info:
        director._adjudicate_action(action, sample_world_state, test_persona)
    
    assert exc_info.value.code == "E004_LOGIC_VIOLATION"

def test_iron_law_5_canon_breach(director, sample_world_state, test_persona):
    """Test Iron Law 5: Canon preservation."""
    
    action = CharacterAction(
        action_type="scan",
        target=None,
        intent="Use impossible_technology to scan area",
        justification="Need advanced scanning",
        confidence=0.6
    )
    
    with pytest.raises(AdjudicationError) as exc_info:
        director._adjudicate_action(action, sample_world_state, test_persona)
    
    assert exc_info.value.code == "E005_CANON_BREACH"

def test_action_repair_mechanism(director, sample_world_state, test_persona):
    """Test that actions can be automatically repaired."""
    
    # Set low energy to trigger repair
    persona_entity = Entity(
        id="agent_1",
        type="character",
        pos="0,0",
        assets={"energy": 5}
    )
    sample_world_state.entities[0] = persona_entity
    
    action = CharacterAction(
        action_type="attack",
        target="enemy_1",
        intent="Full attack", 
        justification="Must attack",
        confidence=0.9
    )
    
    # Should automatically repair to scan action
    result = director._adjudicate_action(action, sample_world_state, test_persona)
    assert result is True  # Repair succeeded

def test_valid_action_passes(director, sample_world_state, test_persona):
    """Test that valid actions pass all checks."""
    
    # Set up valid conditions
    persona_entity = Entity(
        id="agent_1", 
        type="character",
        pos="0,0",
        assets={"energy": 100, "weapon": True}
    )
    sample_world_state.entities[0] = persona_entity
    
    action = CharacterAction(
        action_type="scan",
        target=None,
        intent="Assess battlefield",
        justification="Need situational awareness", 
        confidence=0.8
    )
    
    result = director._adjudicate_action(action, sample_world_state, test_persona)
    assert result is True
```

This implementation pattern demonstrates how to:

1. **Structure validation logic** around the 5 Iron Laws
2. **Implement specific checks** for each law with detailed error codes
3. **Create automatic repair mechanisms** for common failures
4. **Test all failure modes** systematically
5. **Handle edge cases** gracefully with logging

The pattern ensures that all actions are validated against the established rules while providing mechanisms for automatic correction when possible.

---

## 📊 Remaining Work Orders (PR-07 & PR-08)

The patterns for PR-07 (Evaluation & Replay) and PR-08 (Caching & Budgets) follow similar structured approaches:

- **PR-07**: Evaluation pipeline with metrics collection, baseline reporting, and replay logging
- **PR-08**: State hashing, semantic caching, and token budget management

Each maintains the same code quality standards, comprehensive error handling, and test coverage requirements established in the previous patterns.

---

## 🎯 Usage Guidelines

### Pattern Selection
1. **Copy the relevant pattern** for your Work Order
2. **Adapt the examples** to your specific requirements  
3. **Implement tests first** (TDD approach)
4. **Run validation** against existing documentation

### Integration Points
- All patterns integrate with `src/shared_types.py` schemas
- Error handling follows consistent `AdjudicationError` patterns
- Logging uses structured format with context
- Tests use consistent fixtures and naming

### Quality Standards
- **Type Coverage**: 100% type annotations
- **Test Coverage**: 90%+ line coverage
- **Documentation**: Docstrings for all public interfaces
- **Error Handling**: Explicit error codes and messages

These patterns provide the foundation for implementing all 8 Work Orders with consistency and quality.