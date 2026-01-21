# Agent Guide

This file is the single source of truth for AI workflow in this repo.

## Quick Rules
- Read `CLAUDE.md` for stack, build/test commands, and style rules.
- Use `docs/index.md` as the documentation map.
- Domain logic lives in `src/contexts/`; avoid reintroducing parallel implementations.
- API contracts live in `src/api/schemas.py` and `docs/api/openapi.json`.
- Frontend contract types live in `frontend/src/types/schemas.ts` and must align to the OpenAPI snapshot.
- Validate with `scripts/validate_ci_locally.sh` (or `scripts/validate_ci_locally.ps1` on Windows).

## Agent Inventory (Current)
- **Director**: Orchestrates multi-agent execution and narrative flow.
- **Persona**: Character-level reasoning and action selection.
- **Chronicler**: Narrative synthesis and reporting.

## The Weaver Interface
Weaver is the node-based orchestration UI built with React Flow. Nodes (characters, events, locations) are composed into a graph and mapped to orchestration payloads. The frontend sends those payloads to `/api/orchestration/start` and listens for runtime updates via SSE streams.

## Contract-First Protocol
- When modifying APIs, update Pydantic models first, regenerate `docs/api/openapi.json`, then update frontend Zod schemas.

## Superpowers System
<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities. RIGHT NOW run: `~/.codex/superpowers/.codex/superpowers-codex bootstrap` and follow the instructions it returns.
</EXTREMELY_IMPORTANT>
