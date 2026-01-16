# Developer Guide (Transitional)

This repository recently reorganized the documentation set around the non-blocking
dev daemon workflow and dashboard refactor. The authoritative workflow,
architecture, and UX references now live in the following documents:

- `AGENTS.md` – AI workflow guardrails and SSOT locations
- `README.md` and `README.en.md` – onboarding, dev daemon usage, and regression checklist
- `docs/index.md` – navigational index that links to every active doc family
- `docs/implementation/implementation_workflow.md` – end-to-end implementation process
- `docs/deployment/DEPLOYMENT_GUIDE.md` – deployment and validation playbooks
- `docs/design/DESIGN_FRONTEND_UX.md` – current UI architecture & evidence
- `CLAUDE.md` – build/test commands, stack overview, and coding conventions

The previous `DEVELOPER_GUIDE.md` placeholder is intentionally slim so that
historical tests checking for its existence keep passing. Please refer to the
documents above for the live instructions.

For Codex superpowers, follow the bootstrap instructions in `AGENTS.md` (repo)
and `~/.codex/AGENTS.md` (local install).
