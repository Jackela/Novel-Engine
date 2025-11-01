# Novel Engine (AI Narrative Engine)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)

Languages: English | [简体中文](README.md)

Production-ready AI-driven narrative generation and multi-agent simulation platform, with frontend/backend collaboration, observability, and continuous delivery.

This monorepo uses the root README as the single authoritative project homepage. Subdirectory docs are now indexed with non-README filenames to avoid duplication.

---

## Highlights

- Multi-agent architecture: `DirectorAgent`, `PersonaAgent`, `ChroniclerAgent`
- Real AI integration: LLM/external APIs with graceful degradation when unavailable
- Unified configuration: `config.yaml` + environment overrides, thread-safe global access
- Production-ready: concurrency-safe, rich logging, caching & retries, error handling & observability
- Frontend: isolated `frontend/` (React 18) with design system and quality gates

---

## Theoretical Foundation

This project is grounded in Roland Barthes’ 1967 essay “The Death of the Author.” Meaning is not dictated by an author’s singular intent; it emerges from the interplay of language systems and readers. Language precedes the author—what we call “the Human Writing System,” a socially shared symbolic memory spanning language, culture, and corpora. In this view, creation is retrieval and recombination rather than ex nihilo invention.

- Reframed role: within the system, the “author” becomes the “orchestrator.” Novel Engine does not “create meaning”; it generates paths through a semantic network.
- Value proposition: focus on compositional logic, semantic constraints, and reproducibility—not surface-level linguistic novelty.
- Core assumptions and constraints:
  - Language as closed world, open composition: modules compose within existing semantic distributions without escaping the statistical bounds of human language.
  - Composition as constraint: every generation must satisfy logical consistency, semantic coherence, and provenance.
  - Originality as rare recombination: “original” outputs are low-probability new paths in the semantic graph.
- Engineering implications:
  - Path diversification
  - Entropy-balanced generation
  - Validation-driven orchestration
  - Retrieval mechanisms and traceable weighting

See: `docs/FOUNDATIONS.en.md`

---

## Repository Structure (excerpt)

- `src/`: core backend services
- `frontend/`: React app and design system
- `docs/`: architecture, API, guides, ADRs
- `tests/`: test suites and quality gates
- `scripts/`: local validation, quality, migration scripts
- `.github/workflows/`: CI/CD workflows

See the root directory listing and `docs/INDEX.md` for more.

---

## Quick Start

Prereqs: Python 3.11+, Node.js 18+, npm

Backend (example)

```
python -m venv .venv
./.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -U pip
pip install -r requirements.txt
pytest -q  # optional quick tests
python api_server.py  # or production entry points
```

Frontend (example)

```
cd frontend
npm ci
npm run build:tokens
npm run dev
```

---

## Testing & Quality

- Python tests: `pytest` (see `pytest.ini` / `.coveragerc`)
- Local CI parity: `scripts/validate_ci_locally.sh` (Windows: `scripts/validate_ci_locally.ps1`)
- Frontend gates: `npm run type-check`, `npm run lint:all`, `npm run tokens:check`

---

## Documentation

- Docs Home: `docs/INDEX.md`
- Architecture: `docs/architecture/INDEX.md`
- API: `docs/api/INDEX.md`
- Guides: `docs/guides/INDEX.md`

---

## Contributing

Contributions welcome via Issues and PRs. Please run local validation and tests before submitting to satisfy quality gates.

---

## License

MIT License. See `LICENSE`.

