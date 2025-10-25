# Novel-Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://reactjs.org/)

An AI-powered narrative generation platform built on Barthes' "Death of the Author" philosophy, featuring multi-agent orchestration, semantic retrieval, and validation-driven composition.

---

## 🧠 Philosophy

### 1) Theoretical Foundation

#### Background and Intellectual Origins

This project's theoretical foundation derives from Roland Barthes' seminal 1967 essay **"La mort de l'auteur" (The Death of the Author)"**. Barthes argued that the meaning of a text is not determined by the author's singular intent, but rather emerges through the interplay between language systems and readers. Language, in writing, exists prior to the author—it is a socially shared symbolic structure.

This implies: **The author is no longer the center of meaning; language and cultural systems are.**

Novel-Engine inherits and extends this philosophy, transforming "the death of the author" into a computational model hypothesis:

> All texts originate from the **"Human Writing System"**—a symbolic storage system composed of language, culture, corpus, and collective memory. Therefore, the essence of creation is retrieval and recombination, not creation ex nihilo.

#### From Author to Orchestrator: Engineering Philosophy

When this philosophy is translated into engineering implementation, the system's design goal is no longer to "imitate an author writing," but rather to **construct a mechanism capable of retrieving, recombining, and validating text from semantic space**. In other words, the "author" in the system steps down to become an **"Orchestrator."**

| Philosophical Concept | System Correspondence | Functional Meaning |
|----------------------|----------------------|-------------------|
| Author | Orchestrator | Coordinates modules and triggers workflows, but does not directly determine content |
| Language System | Knowledge Base (Semantic Repository) | Holds all potential expressions in the symbolic set |
| Reader | Validation Agent | Evaluates consistency and interpretability post-generation |
| Text | Output Artifact | The result of multi-source information recombination, traceable and reproducible |

This means: Novel-Engine does not generate meaning—it **generates paths through semantic networks**. The system's value lies in combinatorial logic, semantic constraints, and reproducibility, not linguistic surface creativity.

---

### 2) Design Hypotheses and Engineering Constraints

At the engineering level, this philosophy translates into three core hypotheses and constraints:

#### Hypothesis 1: Language as Closed-World, Open Composition
**Principle**: Modules only perform composition within existing semantic distributions and do not break through the statistical boundaries of human language.

**Engineering Implication**: 
- Requires **retrieval mechanisms** to find relevant semantic units
- Demands **traceable weighting** for explainability
- Implementation: Semantic vector spaces, knowledge graphs, weighted retrieval

#### Hypothesis 2: Composition as Constraint
**Principle**: All generation must satisfy logical consistency, semantic coherence, and source traceability constraints.

**Engineering Implication**:
- System architecture adopts **validation-driven orchestration**
- Multi-stage validation gates ensure output quality
- Implementation: Rule engines, constraint solvers, provenance tracking

#### Hypothesis 3: Originality as Rare Recombination
**Principle**: Originality is no longer "from personal inspiration," but a low-probability new path in the semantic graph.

**Engineering Implication**:
- Requires support for **path diversification search**
- Implements **entropy-balanced generation** to avoid repetition
- Implementation: Monte Carlo tree search, temperature-controlled sampling, novelty metrics

---

### 3) From Philosophy to Architecture: System Mapping

The philosophical concept is ultimately formalized into a hierarchical system structure:

```
┌─────────────────────────────────────────────────────────────┐
│ Semantic Space                                               │
│ ├─ Knowledge Base: All potential text units                 │
│ ├─ Semantic Relations: Contextual associations              │
│ └─ Cultural Memory: Collective narrative patterns           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Retrieval Module                                             │
│ ├─ Constraint-Based Search: Find candidates matching rules  │
│ ├─ Weighted Ranking: Prioritize by relevance                │
│ └─ Diversity Sampling: Ensure path novelty                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Orchestration Layer                                          │
│ ├─ Logic Rules: Combine candidates by narrative logic       │
│ ├─ Style Guidelines: Maintain consistent voice              │
│ └─ Provenance Tracking: Record source of each element       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Validation Agents                                            │
│ ├─ Logical Consistency: Ensure no contradictions            │
│ ├─ Style Balance: Check aesthetic coherence                 │
│ └─ Source Legitimacy: Verify provenance                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Output Synthesis                                             │
│ ├─ Final Text Generation                                    │
│ ├─ Provenance Metadata                                      │
│ └─ Quality Metrics                                          │
└─────────────────────────────────────────────────────────────┘
```

This architecture makes Novel-Engine a **symbolic-statistical hybrid system**, dynamically balancing between linguistic statistical patterns and semantic logical constraints.

---

### 4) Cultural and Technical Implications

This project addresses a fundamental question in the era of generative AI:

> **"When both machines and humans generate text from the same corpus system, how can originality persist?"**

Novel-Engine's answer:

> The future of creation lies not in individuals, but in systems—through retrieval, recombination, and validation of semantic memory, it generates **collective recomposition of knowledge**.

In this paradigm:
- **Authors** become curators of semantic paths
- **Readers** become validators of narrative coherence
- **Texts** become traceable artifacts of collective memory
- **Originality** emerges from novel connections, not ex nihilo creation

This philosophical stance positions Novel-Engine not just as a text generator, but as an exploration of **how knowledge and narrative evolve in the age of computational semantics**.

---

## 🌟 Features

### Multi-Agent Architecture
- **DirectorAgent**: Orchestrates narrative turns and manages world state
- **PersonaAgent**: Character AI with Gemini API integration for dynamic decision-making
- **ChroniclerAgent**: Transforms events into dramatic narratives
- **ConfigurationManager**: Centralized configuration with environment variable support

### AI Integration
- **Gemini API Integration**: Real-time LLM-powered character decision-making
- **Intelligent Fallback**: Graceful degradation when API is unavailable
- **Dynamic Prompting**: Context-aware prompt construction
- **Enhanced Narratives**: AI-assisted story generation

### Production Features
- **Thread-Safe Operations**: Concurrent execution support
- **Comprehensive Error Handling**: Graceful degradation
- **Performance Optimized**: Caching, connection pooling, resource management
- **Extensive Logging**: Debug-friendly logging system

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Set up Gemini API
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### Basic Usage

```python
from run_simulation import main

# Run simulation
main()
```

---

## ⚙️ Configuration

The system uses YAML configuration with environment variable overrides:

```yaml
# config.yaml
simulation:
  turns: 3
  max_agents: 10
  api_timeout: 30

paths:
  character_sheets_path: .
  log_file_path: campaign_log.md
  output_directory: narratives

characters:
  default_sheets:
    - character_1.md
    - character_2.md
```

Environment variable overrides:

```bash
export NOVEL_ENGINE_SIMULATION_TURNS=5
export NOVEL_ENGINE_OUTPUT_DIRECTORY="custom_output"
```

---

## 🔧 Architecture

Novel-Engine implements a validation-driven orchestration system:

1. **Semantic Space**: Repository of all potential text units
2. **Retrieval Module**: Constraint-based search and ranking
3. **Orchestration Layer**: Logic-driven candidate combination
4. **Validation Agents**: Multi-stage quality gates
5. **Output Synthesis**: Final text with provenance metadata

For detailed architecture, see `docs/architecture.md`.

---

## 📊 Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html
```

### Adding Characters

Create character sheets in markdown format:

```markdown
# Character Sheet: Character Name

name: Character Name
personality_traits: [Trait1, Trait2, Trait3]

## Core Identity
- **Name**: Full character name
- **Background**: Character background

## Psychological Profile
### Personality Traits
- **Trait1**: Description
- **Trait2**: Description
```

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

---

## 🛡️ Security

- Input validation for all user-provided data
- Safe handling of API keys and credentials
- No execution of untrusted code from AI responses
- Comprehensive error handling prevents information disclosure

---

*For more information, see the [Chinese README](README_ZH.md).*
