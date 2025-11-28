# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Visual documentation with current screenshots in README
- GitHub community files (CONTRIBUTING.md, SECURITY.md, CHANGELOG.md)
- MFD (Multi-Function Display) screenshots for NET, TIME, SIG modes
- Mobile responsive view documentation

### Changed
- Updated README.md with feature preview section
- Updated README.en.md with feature preview section

## [0.1.0] - 2025-11-14

### Added
- Multi-agent architecture with DirectorAgent, PersonaAgent, ChroniclerAgent
- Flow-based dashboard with semantic zones
- Real-time SSE event streaming
- MFD (Multi-Function Display) with DATA, NET, TIME, SIG modes
- User Participatory Interaction (Decision Dialog) feature
- Mobile-responsive tabbed dashboard
- Unified dev environment scripts (dev:daemon, dev:stop, dev:status)
- Comprehensive E2E test suite with Playwright
- Design token system with WCAG AA compliance
- OpenSpec spec-driven development workflow

### Technical Stack
- Backend: FastAPI, Pydantic, asyncio, Redis
- Frontend: React 18, TypeScript, Redux Toolkit, MUI v5
- Testing: pytest, Vitest, Playwright
- CI/CD: GitHub Actions with quality gates

---

## Version History Notes

- **[Unreleased]**: Changes not yet released
- **[0.1.0]**: Initial documented release with core features
