# Novel Engine (AI Narrative Engine)

Languages: English | [简体中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready AI-driven narrative generation and multi-agent simulation platform. Built on a **Modular Monolith** architecture with a **Functional Core, Imperative Shell** philosophy, ensuring high cohesion and low coupling for complex narrative orchestration.

---

## 🚀 Key Features

- **Multi-Agent Orchestration**: `DirectorAgent`, `PersonaAgent`, and `ChroniclerAgent` collaborate via an event bus, ensuring decoupled logic.
- **Guest-First Architecture**: Powered by **Filesystem Workspaces**, enabling zero-config startup, instant demos, and full persistence without external databases.
- **Real-Time Streaming**: Backend `/api/events/stream` (SSE) paired with frontend `useRealtimeEvents` hooks for millisecond-latency narrative feedback.
- **Unified API Surface**: Consistent `/api/*` routing across the stack, backed by an SSOT frontend client with automatic error normalization.
- **Production-Grade Quality**:
  - Frontend: TypeScript Strict + ESLint (SOLID) + Vitest (80% coverage enforcement).
  - Backend: Mypy type checking + Pytest unit/integration suites.

![Dashboard Preview](docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

---

## 🏗️ Architecture Overview

Inspired by **Domain-Driven Design (DDD)** and the **"Death of the Author"** theory.

- **Logical Microservices**: While the codebase resides in a monorepo (`src/`), logic is strictly isolated by domain contexts (`characters`, `narratives`, `orchestration`).
- **File-as-Data**: For maximum portability and local-first UX, all characters, campaign states, and logs are persisted as Markdown, YAML, or JSON on the local filesystem.
- **API-First**: Frontend and backend communicate exclusively via standardized REST APIs, supporting OpenAPI specifications.

---

## 🛠️ Quick Start

### Requirements
- Python 3.11+
- Node.js 18+ & npm

### One-Command Dev Environment (Recommended)

1. **Install Dependencies**:
   ```bash
   # Backend
   python -m venv .venv
   # Windows: .venv\Scripts\activate | Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt

   # Frontend
   cd frontend
   npm install
   ```

2. **Start Services**:
   ```bash
   # Run from root directory
   npm run dev:daemon
   ```
   - Backend API: `http://127.0.0.1:8000`
   - Frontend UI: `http://127.0.0.1:3000`
   - Logs are streamed to `tmp/dev_env.log`.

3. **Stop Services**:
   ```bash
   npm run dev:stop
   ```

---

## 📂 Project Structure

```
Novel-Engine/
├── src/                  # Backend Core (FastAPI + Agents)
│   ├── api/              # API Routers & App Factory
│   ├── agents/           # Agent Logic (Director, Persona)
│   ├── contexts/         # DDD Context Boundaries
│   └── workspaces/       # Filesystem Persistence Layer
├── frontend/             # Frontend App (React + Vite)
│   ├── src/lib/api/      # SSOT API Client
│   ├── src/features/     # Business Feature Modules
│   └── tests/            # Vitest & Playwright Suites
├── docs/                 # Architecture & Guides
├── openspec/             # Architecture Evolution Proposals
└── characters/           # User Data (YAML/MD)
```

---

## 🧪 Testing & Quality

We enforce a strict TDD (Test-Driven Development) workflow.

- **Backend**:
  ```bash
  pytest
  ```
- **Frontend**:
  ```bash
  cd frontend
  npm run test        # Unit Tests (Vitest)
  npm run lint        # Style & Complexity Checks
  npm run type-check  # TypeScript Validation
  ```
- **E2E / UAT**:
  UI changes must be verified via Playwright:
  ```bash
  cd frontend
  npx playwright test
  ```

---

## 🤝 Contributing

1. Follow standards in `docs/coding-standards.md`.
2. Run local validation: `scripts/validate_ci_locally.sh` before pushing.
3. Propose architectural changes via `openspec`.

---

## 📄 License

MIT License. See [LICENSE](LICENSE).