# Chunking Strategy Refactor Plan

## Overview

**Source File**: `src/contexts/knowledge/infrastructure/adapters/chunking_strategy_adapters.py`  
**Current Size**: 2,531 lines  
**Target Architecture**: Strategy Pattern with clean separation  
**Architecture Goal**: Hexagonal - Each strategy as independent adapter

---

## Current Structure Analysis

### File Sections

```
Lines   Component                          Responsibility
-----   ---------                          ------------
1-53    Header & Imports                   Module docstring, imports
54-124  CoherenceScore dataclass           Score representation
125-470 ChunkCoherenceAnalyzer             Semantic coherence analysis
471-674 FixedChunkingStrategy              Fixed-size chunking
675-904 SentenceChunkingStrategy           Sentence-aware chunking
905-1132 ParagraphChunkingStrategy          Paragraph-aware chunking
1133-1522 SemanticChunkingStrategy         Semantic/embedding chunking
1523-2144 NarrativeFlowChunkingStrategy    Narrative-aware chunking
2145-2161 ContentType enum                 Content type classification
2162-2531 AutoChunkingStrategy             Auto-selection strategy
```

### Strategy Classes Detail

| Class | Lines | Complexity | Description |
|-------|-------|------------|-------------|
| FixedChunkingStrategy | 204 | Low | Fixed-size with overlap |
| SentenceChunkingStrategy | 230 | Medium | Sentence boundary aware |
| ParagraphChunkingStrategy | 228 | Medium | Paragraph boundary aware |
| SemanticChunkingStrategy | 390 | High | Embedding-based grouping |
| NarrativeFlowChunkingStrategy | 622 | Very High | Story structure aware |
| AutoChunkingStrategy | 370 | High | Content-type based selection |

### Shared Components

| Component | Lines | Responsibility |
|-----------|-------|----------------|
| CoherenceScore | 71 | Immutable score data |
| ChunkCoherenceAnalyzer | 346 | Coherence calculation utilities |
| ContentType | 17 | Content classification enum |

---

## Target Architecture (Strategy Pattern)

```
src/contexts/knowledge/infrastructure/adapters/chunking/
├── __init__.py                      # Public exports, factory registration
├── base.py                          # Abstract base strategy
├── coherence.py                     # Coherence scoring & analysis
├── content_type.py                  # Content type classification
├── factory.py                       # StrategyFactory
├── strategies/
│   ├── __init__.py
│   ├── fixed.py                     # FixedChunkingStrategy (~200 lines)
│   ├── sentence.py                  # SentenceChunkingStrategy (~230 lines)
│   ├── paragraph.py                 # ParagraphChunkingStrategy (~230 lines)
│   ├── semantic.py                  # SemanticChunkingStrategy (~400 lines)
│   ├── narrative.py                 # NarrativeFlowChunkingStrategy (~630 lines)
│   └── auto.py                      # AutoChunkingStrategy (~380 lines)
└── utils.py                         # Shared utilities, regex patterns
```

---

## Class Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      IChunkingStrategy                       │
│                      (Port Interface)                        │
├─────────────────────────────────────────────────────────────┤
│ + async chunk(text, config) -> list[Chunk]                  │
│ + supports_strategy_type(strategy_type: str) -> bool        │
└─────────────────────────────────────────────────────────────┘
                              △
                              │ implements
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐    ┌───────┴───────┐    ┌───────┴───────┐
│ BaseChunking  │    │  Coherence    │    │ ContentType   │
│   Strategy    │    │   Analyzer    │    │    Enum       │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ # _word_count │    │ # analyze()   │    │ NARRATIVE     │
│ # _fallback   │    │ # _calculate  │    │ TECHNICAL     │
└───────────────┘    └───────────────┘    └───────────────┘
        △
        │ extends
   ┌────┴────┬────────┬──────────┬───────────┬────────┐
   │         │        │          │           │        │
┌──┴──┐  ┌──┴───┐ ┌──┴────┐ ┌───┴────┐ ┌───┴────┐ ┌──┴──┐
│Fixed│  │Sentence│ │Paragraph│ │Semantic│ │Narrative│ │Auto │
└─────┘  └────────┘ └─────────┘ └────────┘ └─────────┘ └─────┘
```

---

## Module Specifications

### 1. `chunking/__init__.py` (~80 lines)

**Responsibilities**: Public API exports, convenient imports

```python
"""Chunking strategies package.

Provides various text chunking implementations for RAG processing.
"""

from .base import BaseChunkingStrategy
from .coherence import ChunkCoherenceAnalyzer, CoherenceScore
from .content_type import ContentType
from .factory import StrategyFactory
from .strategies.auto import AutoChunkingStrategy
from .strategies.fixed import FixedChunkingStrategy
from .strategies.narrative import NarrativeFlowChunkingStrategy
from .strategies.paragraph import ParagraphChunkingStrategy
from .strategies.semantic import SemanticChunkingStrategy
from .strategies.sentence import SentenceChunkingStrategy

__all__ = [
    # Base
    "BaseChunkingStrategy",
    # Coherence
    "ChunkCoherenceAnalyzer",
    "CoherenceScore",
    # Content Type
    "ContentType",
    # Factory
    "StrategyFactory",
    # Strategies
    "AutoChunkingStrategy",
    "FixedChunkingStrategy",
    "NarrativeFlowChunkingStrategy",
    "ParagraphChunkingStrategy",
    "SemanticChunkingStrategy",
    "SentenceChunkingStrategy",
]


def get_strategy(strategy_type: str) -> BaseChunkingStrategy:
    """Factory function for getting strategies by type."""
    return StrategyFactory.get_strategy(strategy_type)
```

### 2. `chunking/base.py` (~100 lines)

**Responsibilities**: Abstract base class for all chunking strategies

```python
"""Base chunking strategy with common utilities."""

from abc import ABC, abstractmethod
from typing import Optional

from src.contexts.knowledge.application.ports.i_chunking_strategy import (
    Chunk,
    IChunkingStrategy,
)
from src.contexts.knowledge.domain.models.chunking_strategy import ChunkingStrategy


class BaseChunkingStrategy(IChunkingStrategy, ABC):
    """Abstract base class for all chunking strategies.
    
    Provides common functionality:
    - Word counting
    - Fallback mechanisms
    - Configuration validation
    """
    
    def _word_count(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def _fallback_fixed(
        self, 
        text: str, 
        config: ChunkingStrategy
    ) -> list[Chunk]:
        """Fallback to fixed-size chunking."""
        from .strategies.fixed import FixedChunkingStrategy
        return await FixedChunkingStrategy().chunk(text, config)
    
    @abstractmethod
    async def chunk(
        self,
        text: str,
        config: Optional[ChunkingStrategy] = None,
    ) -> list[Chunk]:
        """Split text into chunks."""
        ...
    
    @abstractmethod
    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if strategy supports the given type."""
        ...
```

### 3. `chunking/coherence.py` (~350 lines)

**Responsibilities**: Coherence scoring and analysis

```python
"""Coherence scoring for chunk quality assessment."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseChunkingStrategy


@dataclass(frozen=True, slots=True)
class CoherenceScore:
    """Immutable coherence score for a chunk."""
    score: float
    internal_coherence: float
    boundary_quality: float
    size_score: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    is_acceptable: bool = True

    def __post_init__(self) -> None:
        """Validate and normalize scores."""
        ...


class ChunkCoherenceAnalyzer:
    """Analyzes coherence of chunks using embedding similarity.
    
    Provides methods for:
    - Calculating internal coherence
    - Evaluating boundary quality
    - Scoring size appropriateness
    - Generating quality warnings
    """
    
    def __init__(self, embedding_service: Optional["IEmbeddingService"] = None):
        self._embedding_service = embedding_service
    
    async def analyze(self, chunk: Chunk) -> CoherenceScore:
        """Analyze coherence of a single chunk."""
        ...
    
    async def _calculate_internal_coherence(self, sentences: list[str]) -> float:
        """Calculate similarity between adjacent sentences."""
        ...
    
    def _calculate_boundary_quality(self, text: str, start: int, end: int) -> float:
        """Score how well boundaries preserve structure."""
        ...
    
    def _calculate_size_score(self, word_count: int, config: ChunkingStrategy) -> float:
        """Score based on chunk size appropriateness."""
        ...
```

### 4. `chunking/content_type.py` (~50 lines)

**Responsibilities**: Content type classification enum

```python
"""Content type classification for auto chunking."""

from enum import Enum


class ContentType(str, Enum):
    """Types of content for automatic strategy selection."""
    
    NARRATIVE = "narrative"           # Story, dialogue
    TECHNICAL = "technical"           # Documentation, code
    CONVERSATIONAL = "conversational" # Chat, interview
    ACADEMIC = "academic"             # Research papers
    LEGAL = "legal"                   # Contracts, legal docs
    POETRY = "poetry"                 # Verse, lyrics
    UNKNOWN = "unknown"
```

### 5. `chunking/utils.py` (~80 lines)

**Responsibilities**: Shared utility functions and regex patterns

```python
"""Shared utilities for chunking strategies."""

import re

# Word pattern for counting
WORD_PATTERN = re.compile(r"\S+")

# Sentence end pattern: . ! ? followed by whitespace
SENTENCE_END = re.compile(r"[.!?]+\s+", re.MULTILINE)

# Paragraph delimiter: two or more newlines
PARAGRAPH_DELIM = re.compile(r"\n\n+", re.MULTILINE)

# Default coherence threshold
DEFAULT_COHERENCE_THRESHOLD = 0.6
MIN_COHERENCE_THRESHOLD = 0.0
MAX_COHERENCE_THRESHOLD = 1.0


def count_words(text: str) -> int:
    """Count words in text."""
    return len(WORD_PATTERN.findall(text))


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    """Split text into sentences with position tracking.
    
    Returns list of (start_pos, end_pos, sentence_text) tuples.
    """
    ...


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs."""
    return [p.strip() for p in PARAGRAPH_DELIM.split(text) if p.strip()]


def calculate_overlap(text1: str, text2: str) -> float:
    """Calculate overlap ratio between two text segments."""
    ...
```

### 6. `chunking/factory.py` (~100 lines)

**Responsibilities**: Strategy factory for dynamic selection

```python
"""Factory for creating chunking strategies."""

from typing import Optional

from .base import BaseChunkingStrategy
from .strategies.auto import AutoChunkingStrategy
from .strategies.fixed import FixedChunkingStrategy
from .strategies.narrative import NarrativeFlowChunkingStrategy
from .strategies.paragraph import ParagraphChunkingStrategy
from .strategies.semantic import SemanticChunkingStrategy
from .strategies.sentence import SentenceChunkingStrategy


class StrategyFactory:
    """Factory for creating chunking strategy instances.
    
    Provides centralized strategy registration and retrieval.
    Supports lazy initialization and caching.
    """
    
    _strategies: dict[str, type[BaseChunkingStrategy]] = {}
    _instances: dict[str, BaseChunkingStrategy] = {}
    
    @classmethod
    def register(
        cls, 
        strategy_type: str, 
        strategy_class: type[BaseChunkingStrategy]
    ) -> None:
        """Register a strategy class for a type."""
        cls._strategies[strategy_type.lower()] = strategy_class
    
    @classmethod
    def get_strategy(cls, strategy_type: str) -> BaseChunkingStrategy:
        """Get or create strategy instance."""
        strategy_type = strategy_type.lower()
        
        if strategy_type not in cls._instances:
            strategy_class = cls._strategies.get(strategy_type)
            if not strategy_class:
                raise ValueError(f"Unknown strategy type: {strategy_type}")
            cls._instances[strategy_type] = strategy_class()
        
        return cls._instances[strategy_type]
    
    @classmethod
    def get_all_strategies(cls) -> list[BaseChunkingStrategy]:
        """Get all registered strategy instances."""
        return [cls.get_strategy(t) for t in cls._strategies.keys()]


# Auto-register built-in strategies
StrategyFactory.register("fixed", FixedChunkingStrategy)
StrategyFactory.register("sentence", SentenceChunkingStrategy)
StrategyFactory.register("paragraph", ParagraphChunkingStrategy)
StrategyFactory.register("semantic", SemanticChunkingStrategy)
StrategyFactory.register("narrative", NarrativeFlowChunkingStrategy)
StrategyFactory.register("auto", AutoChunkingStrategy)
```

### 7. `chunking/strategies/fixed.py` (~200 lines)

**Responsibilities**: Fixed-size chunking with overlap

```python
"""Fixed-size chunking strategy."""

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from ..base import BaseChunkingStrategy
from ..utils import count_words

logger = structlog.get_logger()


class FixedChunkingStrategy(BaseChunkingStrategy):
    """Chunks text into fixed-size segments with optional overlap.
    
    Best for: General purpose, simple documents
    Trade-offs: May break semantic boundaries
    """
    
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_OVERLAP = 50
    
    async def chunk(self, text: str, config=None) -> list[Chunk]:
        """Split text into fixed-size chunks."""
        if not text or not text.strip():
            return []
        
        chunk_size = config.chunk_size if config else self.DEFAULT_CHUNK_SIZE
        overlap = config.chunk_overlap if config else self.DEFAULT_OVERLAP
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk_text = text[start:end]
            
            chunks.append(Chunk(
                text=chunk_text,
                index=len(chunks),
                metadata={
                    "start": start,
                    "end": end,
                    "word_count": count_words(chunk_text),
                }
            ))
            
            start = end - overlap if end < text_len else end
        
        logger.info("fixed_chunking_complete", chunk_count=len(chunks))
        return chunks
    
    def supports_strategy_type(self, strategy_type: str) -> bool:
        return strategy_type.lower() == ChunkStrategyType.FIXED.value
```

### 8. `chunking/strategies/sentence.py` (~230 lines)

**Responsibilities**: Sentence-aware chunking

```python
"""Sentence-aware chunking strategy."""

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from ..base import BaseChunkingStrategy
from ..utils import SENTENCE_END, count_words

logger = structlog.get_logger()


class SentenceChunkingStrategy(BaseChunkingStrategy):
    """Chunks text at sentence boundaries.
    
    Best for: Preserving sentence structure
    Trade-offs: Variable chunk sizes
    """
    
    async def chunk(self, text: str, config=None) -> list[Chunk]:
        """Split text into sentence-based chunks."""
        ...
    
    def supports_strategy_type(self, strategy_type: str) -> bool:
        return strategy_type.lower() == ChunkStrategyType.SENTENCE.value
```

### 9. `chunking/strategies/paragraph.py` (~230 lines)

**Responsibilities**: Paragraph-aware chunking

```python
"""Paragraph-aware chunking strategy."""

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from ..base import BaseChunkingStrategy
from ..utils import PARAGRAPH_DELIM, count_words

logger = structlog.get_logger()


class ParagraphChunkingStrategy(BaseChunkingStrategy):
    """Chunks text at paragraph boundaries.
    
    Best for: Preserving paragraph structure
    Trade-offs: Very variable chunk sizes
    """
    
    async def chunk(self, text: str, config=None) -> list[Chunk]:
        """Split text into paragraph-based chunks."""
        ...
    
    def supports_strategy_type(self, strategy_type: str) -> bool:
        return strategy_type.lower() == ChunkStrategyType.PARAGRAPH.value
```

### 10. `chunking/strategies/semantic.py` (~400 lines)

**Responsibilities**: Embedding-based semantic chunking

```python
"""Semantic chunking strategy using embeddings."""

from typing import TYPE_CHECKING

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from ..base import BaseChunkingStrategy

if TYPE_CHECKING:
    from ...application.ports.i_embedding_service import IEmbeddingService

logger = structlog.get_logger()


class SemanticChunkingStrategy(BaseChunkingStrategy):
    """Chunks text by semantic similarity using embeddings.
    
    Groups sentences by semantic similarity to create coherent chunks.
    
    Best for: Preserving semantic coherence
    Trade-offs: Requires embedding service, slower
    """
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.7
    DEFAULT_MAX_SENTENCES_PER_CHUNK = 10
    
    def __init__(self, embedding_service: Optional["IEmbeddingService"] = None):
        self._embedding_service = embedding_service
    
    async def chunk(self, text: str, config=None) -> list[Chunk]:
        """Split text into semantically coherent chunks."""
        # 1. Split into sentences
        # 2. Generate embeddings
        # 3. Group by similarity
        # 4. Create chunks
        ...
    
    def supports_strategy_type(self, strategy_type: str) -> bool:
        return strategy_type.lower() == ChunkStrategyType.SEMANTIC.value
```

### 11. `chunking/strategies/narrative.py` (~630 lines)

**Responsibilities**: Narrative-aware chunking

```python
"""Narrative-aware chunking strategy."""

import re
from typing import Optional

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from ..base import BaseChunkingStrategy
from ..coherence import ChunkCoherenceAnalyzer

logger = structlog.get_logger()


class NarrativeFlowChunkingStrategy(BaseChunkingStrategy):
    """Chunks text preserving narrative flow and story structure.
    
    Detects:
    - Scene boundaries
    - Dialogue sections
    - Character transitions
    - Temporal markers
    
    Best for: Fiction, creative writing
    Trade-offs: Complex heuristics, language-dependent
    """
    
    # Scene transition patterns
    SCENE_PATTERNS = [
        r"\n\n+#{1,6}\s+",  # Markdown headers
        r"\n\n+Chapter\s+\d+",  # Chapter markers
        r"\n\n+\*{3,}",  # Scene breaks
        # ... more patterns
    ]
    
    # Dialogue patterns
    DIALOGUE_PATTERNS = [
        r'[""][^""]+[""]',  # Quoted speech
        r"^['\"].+['\"]$",  # Line dialogue
    ]
    
    def __init__(self):
        self._coherence_analyzer = ChunkCoherenceAnalyzer()
    
    async def chunk(self, text: str, config=None) -> list[Chunk]:
        """Split text into narrative-aware chunks."""
        # 1. Detect scenes
        # 2. Identify dialogue sections
        # 3. Track character transitions
        # 4. Create flow-preserving chunks
        ...
    
    def supports_strategy_type(self, strategy_type: str) -> bool:
        return strategy_type.lower() == ChunkStrategyType.NARRATIVE.value
```

### 12. `chunking/strategies/auto.py` (~380 lines)

**Responsibilities**: Auto-selection based on content type

```python
"""Auto-selection chunking strategy."""

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from ..base import BaseChunkingStrategy
from ..content_type import ContentType
from ..factory import StrategyFactory

logger = structlog.get_logger()


class AutoChunkingStrategy(BaseChunkingStrategy):
    """Automatically selects the best chunking strategy.
    
    Analyzes content type and characteristics to choose:
    - NARRATIVE -> NarrativeFlowChunkingStrategy
    - TECHNICAL -> ParagraphChunkingStrategy
    - CONVERSATIONAL -> SentenceChunkingStrategy
    - etc.
    """
    
    # Content type heuristics
    HEURISTICS = {
        ContentType.NARRATIVE: ["chapter", "scene", "character"],
        ContentType.TECHNICAL: ["function", "class", "api"],
        # ... more heuristics
    }
    
    # Strategy mapping
    STRATEGY_MAP = {
        ContentType.NARRATIVE: "narrative",
        ContentType.TECHNICAL: "paragraph",
        ContentType.CONVERSATIONAL: "sentence",
        ContentType.ACADEMIC: "semantic",
        ContentType.LEGAL: "fixed",
        ContentType.POETRY: "sentence",
        ContentType.UNKNOWN: "fixed",
    }
    
    def __init__(self):
        self._content_classifier = ContentClassifier()
    
    async def chunk(self, text: str, config=None) -> list[Chunk]:
        """Auto-select and apply best strategy."""
        content_type = self._detect_content_type(text)
        strategy_type = self.STRATEGY_MAP[content_type]
        strategy = StrategyFactory.get_strategy(strategy_type)
        
        logger.info("auto_strategy_selected", 
                   content_type=content_type.value,
                   strategy=strategy_type)
        
        return await strategy.chunk(text, config)
    
    def supports_strategy_type(self, strategy_type: str) -> bool:
        return strategy_type.lower() == ChunkStrategyType.AUTO.value
    
    def _detect_content_type(self, text: str) -> ContentType:
        """Analyze text to determine content type."""
        ...
```

---

## Migration Steps

### Phase 1: Setup (0.5 day)

1. **Create directory structure**
   ```bash
   mkdir -p src/contexts/knowledge/infrastructure/adapters/chunking/strategies
   touch src/contexts/knowledge/infrastructure/adapters/chunking/__init__.py
   touch src/contexts/knowledge/infrastructure/adapters/chunking/strategies/__init__.py
   ```

2. **Backup original file**
   ```bash
   cp src/contexts/knowledge/infrastructure/adapters/chunking_strategy_adapters.py \
      src/contexts/knowledge/infrastructure/adapters/chunking_strategy_adapters.py.bak
   ```

### Phase 2: Extract Shared Components (Day 1)

1. **Create `chunking/utils.py`**
   - Extract regex patterns
   - Extract utility functions
   - Add unit tests

2. **Create `chunking/content_type.py`**
   - Move `ContentType` enum

3. **Create `chunking/coherence.py`**
   - Move `CoherenceScore` dataclass
   - Move `ChunkCoherenceAnalyzer` class

4. **Create `chunking/base.py`**
   - Define `BaseChunkingStrategy` abstract class

### Phase 3: Extract Strategies (Day 2-3)

For each strategy, in order of complexity:

1. **Fixed** (simplest) - Day 2 morning
2. **Sentence** - Day 2 morning
3. **Paragraph** - Day 2 afternoon
4. **Semantic** - Day 2 afternoon / Day 3 morning
5. **Narrative** - Day 3 morning
6. **Auto** - Day 3 afternoon

Each extraction:
- Copy class to new file
- Update imports
- Run tests
- Verify no regressions

### Phase 4: Factory & Integration (Day 4)

1. **Create `chunking/factory.py`**
   - Implement `StrategyFactory`
   - Auto-register built-in strategies

2. **Create `chunking/__init__.py`**
   - Set up public exports
   - Backward compatibility re-exports

3. **Update `chunking_strategy_adapters.py`**
   - Convert to re-export shim
   - Add deprecation warnings

### Phase 5: Testing & Validation (Day 5)

1. **Run all chunking tests**
   ```bash
   pytest tests/ -k "chunking" -v
   ```

2. **Verify factory registration**
   ```python
   from chunking import StrategyFactory
   assert len(StrategyFactory.get_all_strategies()) == 6
   ```

3. **Performance benchmark**
   - Compare before/after performance
   - Ensure no degradation

### Phase 6: Cleanup (Day 6)

1. **Remove old file**
   ```bash
   rm src/contexts/knowledge/infrastructure/adapters/chunking_strategy_adapters.py
   rm src/contexts/knowledge/infrastructure/adapters/chunking_strategy_adapters.py.bak
   ```

2. **Update imports**
   ```bash
   find src/ -name "*.py" -exec grep -l "chunking_strategy_adapters" {} \;
   ```

3. **Update documentation**

---

## Backward Compatibility

### Shim Module

Create temporary compatibility layer:

```python
# chunking_strategy_adapters.py (temporary shim)
"""Backward compatibility - will be removed in v2.0"""
import warnings

warnings.warn(
    "chunking_strategy_adapters is deprecated, use chunking package",
    DeprecationWarning,
    stacklevel=2
)

from .chunking import (
    AutoChunkingStrategy,
    ChunkCoherenceAnalyzer,
    CoherenceScore,
    ContentType,
    FixedChunkingStrategy,
    NarrativeFlowChunkingStrategy,
    ParagraphChunkingStrategy,
    SemanticChunkingStrategy,
    SentenceChunkingStrategy,
    StrategyFactory,
)

__all__ = [
    "AutoChunkingStrategy",
    "ChunkCoherenceAnalyzer",
    "CoherenceScore",
    "ContentType",
    "FixedChunkingStrategy",
    "NarrativeFlowChunkingStrategy",
    "ParagraphChunkingStrategy",
    "SemanticChunkingStrategy",
    "SentenceChunkingStrategy",
    "StrategyFactory",
]
```

---

## Risk Analysis

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Circular imports | High | Medium | Careful dependency ordering |
| Strategy registration failure | High | Low | Explicit registration in tests |
| Coherence analyzer breaks | Medium | Low | Comprehensive test coverage |
| Performance regression | Medium | Low | Benchmark comparison |
| Factory returns wrong strategy | High | Low | Type checking, unit tests |
| Breaking change detection | High | Low | Import compatibility layer |

---

## Success Criteria

- [ ] Each strategy module <500 lines
- [ ] All existing tests pass
- [ ] Factory returns correct strategy types
- [ ] No circular import errors
- [ ] Performance within 5% of baseline
- [ ] Backward compatibility maintained (deprecation warnings)

---

## Post-Refactoring Opportunities

1. **Plugin System**: Allow custom strategy registration
2. **Configuration**: Strategy-specific config schemas
3. **Metrics**: Track strategy performance/quality
4. **Caching**: Cache strategy instances
5. **Validation**: Pre-chunking content validation
6. **Visualization**: Chunk boundary visualization
