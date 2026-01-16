# Agent Guide

This file is the single source of truth for AI workflow in this repo.

## Quick Rules
- Read `CLAUDE.md` for stack, build/test commands, and style rules.
- Use `docs/index.md` as the documentation map.
- For proposals/specs/architecture changes, open `openspec/AGENTS.md` and follow OpenSpec.
- Domain logic lives in `src/contexts/`; avoid reintroducing parallel implementations.
- API contracts live in `src/api/schemas.py` and `docs/SCHEMAS.md`.
- Validate with `scripts/validate_ci_locally.sh` (or `scripts/validate_ci_locally.ps1` on Windows).

## Superpowers System
<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities. RIGHT NOW run: `~/.codex/superpowers/.codex/superpowers-codex bootstrap` and follow the instructions it returns.
</EXTREMELY_IMPORTANT>
