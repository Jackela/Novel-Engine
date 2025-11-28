# Contributing to Novel Engine

Thank you for your interest in contributing to Novel Engine! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/p3nGu1nZz/Novel-Engine.git
   cd Novel-Engine
   ```

2. Set up the backend:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up the frontend:
   ```bash
   cd frontend
   npm install
   ```

4. Start development environment:
   ```bash
   npm run dev:daemon
   ```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits format:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Process

1. Fork the repository and create your branch from `main`
2. Make your changes following the code style guidelines
3. Write or update tests as needed
4. Run the quality gates:
   ```bash
   # Frontend
   cd frontend
   npm run lint
   npm run type-check
   npm test -- --run

   # Backend
   bash scripts/validate_ci_locally.sh
   ```
5. Update documentation if needed
6. Submit a pull request with a clear description

## Code Style

### Frontend (TypeScript/React)

- Use TypeScript strict mode
- Follow ESLint and Prettier configurations
- Use functional components with hooks
- Maintain `data-role` and `data-testid` attributes for testing

### Backend (Python)

- Follow PEP 8 style guide
- Use type annotations
- Run Black, Isort, Flake8, and Mypy
- Follow DDD principles for domain logic

## Testing Requirements

### Frontend

- Unit tests with Vitest
- E2E tests with Playwright
- Maintain existing test coverage

### Backend

- Unit tests with pytest
- Integration tests for API endpoints
- Security and quality framework tests

## Documentation

- Update README if adding new features
- Document API changes in `docs/api/`
- Add architectural decisions to `docs/architecture/`

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Use discussions for general questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
