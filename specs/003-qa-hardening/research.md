## Research Log — QA Pipeline Hardening

### 1. Repository Formatting Strategy
- **Decision**: Adopt `black==25.x`, `isort==7.x` (profile=black), `flake8==7.x`, and `mypy==1.18+` as enforced standards; run across `src/`, `tests/`, `ai_testing/`, and key script directories.  
- **Rationale**: Aligns with GitHub Actions job requirements and minimizes tool drift; modern versions support Python 3.12 and new typing features.  
- **Alternatives Considered**:  
  - *Keep existing mixed formatting*: fails CI and complicates reviews.  
  - *Use Ruff in place of black/flake8*: desirable long term but higher adoption overhead now.

### 2. Integration Test Stabilization
- **Decision**: Investigate `TestTurnOrchestrationE2E` dependencies, provision deterministic fixtures (mocked phase tracker or seeded data), and normalize return values (avoid `return True` patterns).  
- **Rationale**: Failure stems from missing setup; providing explicit fixtures and replacing `return` with assertions brings tests in line with pytest conventions.  
- **Alternatives Considered**:  
  - *Skip problematic test*: hides regression risk; unacceptable.  
  - *Rewrite entire orchestration flow*: excessive scope for QA hardening.

### 3. QA Tooling Environment
- **Decision**: Update `scripts/validate_ci_locally.sh` to create `.venv-ci`, install dependencies with `pip --break-system-packages` fallback, install Playwright browsers, and run formatting/tests sequentially with clear logging. Document prerequisites (Docker, act, Python 3.11+).  
- **Rationale**: Current script fails on Debian-based systems lacking `pip`. Virtualenv approach avoids system-level installation errors.  
- **Alternatives Considered**:  
  - *Rely on system python*: blocked by PEP 668 restrictions.  
  - *Use Poetry/pipenv*: heavier change with broader repo impact.

### 4. GitHub Actions Optimization
- **Decision**: Update `.github/workflows/quality_assurance.yml` to reuse new formatting/test scripts, leverage caching for `.venv-ci`, and adjust job timeouts (increase to 25 minutes). Add ignore files/artifacts to reduce CI churn.  
- **Rationale**: Running formatters/tests directly in workflow reduces duplication and ensures parity with local script.  
- **Alternatives Considered**:  
  - *Leave workflow unchanged*: perpetuates failures/timeouts.  
  - *Split jobs per directory*: could help but extra complexity; revisit after formatting baseline applied.

### 5. Documentation & Communication
- **Decision**: Update README/QA docs with QA quickstart, prerequisites (Docker, act, Playwright install), and link to new tooling scripts. Provide guidance for Windows contributors (WSL usage) and act Docker image size considerations.  
- **Rationale**: Prevent future onboarding confusion and ensures constitution’s documentation stewardship principle satisfied.  
- **Alternatives Considered**:  
  - *Inline comments only*: insufficient for new contributors.
