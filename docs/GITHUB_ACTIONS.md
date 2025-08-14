# GitHub Actions CI/CD Setup

This document describes the GitHub Actions workflows and local testing setup for the Novel Engine project.

## 🚀 Overview

The project uses GitHub Actions for continuous integration, testing, and deployment with the following workflows:

- **CI Pipeline** (`ci.yml`) - Main testing and build workflow
- **Staging Deployment** (`deploy-staging.yml`) - Automated staging deployments
- **Production Release** (`release.yml`) - Release management and production deployment
- **Local Testing** (`local-test.yml`) - Optimized for local development with `act`

## 📁 Project Structure Analysis

**Novel Engine** is a Python-based Warhammer 40k Multi-Agent Simulator with:
- **Backend**: Python FastAPI server with SQLite database
- **Frontend**: React/TypeScript application with Vite
- **Testing**: Playwright E2E tests + pytest unit tests
- **Dependencies**: Python `requirements.txt` + Node.js `package.json`

## 🔄 CI/CD Workflows

### 1. CI Pipeline (`ci.yml`)

**Triggers**: Push/PR to `main`, `develop` branches + manual dispatch

**Jobs**:
- **backend-tests**: Python linting, type checking, unit tests with coverage
- **frontend-tests**: Node.js linting, type checking, unit tests with coverage
- **e2e-tests**: Full-stack integration testing with Playwright
- **security**: Vulnerability scanning with Trivy, Safety, Bandit
- **build**: Package creation and artifact generation

**Key Features**:
- Parallel job execution for speed
- Code coverage reporting to Codecov
- Security scanning and vulnerability detection
- Artifact generation for deployments

### 2. Staging Deployment (`deploy-staging.yml`)

**Triggers**: Push to `develop` branch + manual dispatch with force option

**Jobs**:
- **health-check**: Quick smoke tests before deployment
- **deploy-staging**: Deployment to staging environment with health checks

**Features**:
- Environment-specific deployment
- Automated health checks
- Deployment rollback capability
- Optional force deployment

### 3. Production Release (`release.yml`)

**Triggers**: Git tags (`v*`) + manual dispatch

**Jobs**:
- **build-release**: Full test suite + distribution package creation
- **deploy-production**: Production deployment (manual approval required)

**Features**:
- Automated changelog generation
- GitHub release creation with assets
- Production environment protection
- Complete test validation before release

### 4. Local Testing (`local-test.yml`)

**Purpose**: Optimized workflow for local development with `act`

**Features**:
- Fast execution without external dependencies
- Simplified testing for rapid iteration
- Integration smoke tests
- Docker-friendly configuration

## 🏠 Local Testing with `act`

### Installation

`act` is already installed on this system at: `E:\act_Windows_x86_64\act.exe`

For other systems:
```bash
# Windows (winget)
winget install nektos.act

# macOS (Homebrew)
brew install act

# Linux (manual install)
curl -sL https://raw.githubusercontent.com/nektos/act/master/install.sh | bash
```

### Configuration Files

#### `.actrc` - Act Configuration
```
# Use medium-sized runner image
-P ubuntu-latest=catthehacker/ubuntu:act-latest

# Enable verbose output and reuse containers
--verbose
--reuse

# Set secrets and artifacts
--secret-file .env.local
--artifact-server-path ./act-artifacts
```

#### `.env.local` - Local Environment Variables
```bash
# GitHub token (optional, helps with rate limits)
GITHUB_TOKEN=your_github_token_here

# Python environment
PYTHONPATH=/github/workspace

# Test environment flags
CI=true
GITHUB_ACTIONS=true
ACT_LOCAL=true

# API keys (use test values)
GEMINI_API_KEY=test_key_for_local_testing

# Database configuration
DATABASE_URL=sqlite:///tmp/test.db

# Frontend settings
VITE_API_URL=http://localhost:8000
VITE_NODE_ENV=test
```

### Running Local Tests

#### PowerShell Script (`act-runner.ps1`)
```powershell
# List all workflows
.\act-runner.ps1 -List

# Run simple test workflow
.\act-runner.ps1 -Workflow simple-test

# Run specific CI job
.\act-runner.ps1 -Workflow ci -Job backend-tests

# Dry run to see what would execute
.\act-runner.ps1 -Workflow local-test -DryRun

# Verbose output for debugging
.\act-runner.ps1 -Workflow simple-test -Verbose

# Clean up Docker resources
.\act-runner.ps1 -Clean
```

#### Bash Script (`act-runner.sh`)
```bash
# Make executable
chmod +x act-runner.sh

# List workflows
./act-runner.sh --list

# Run simple test
./act-runner.sh -w simple-test

# Run with verbose output
./act-runner.sh -w local-test --verbose

# Clean up
./act-runner.sh --clean
```

#### Direct `act` Commands
```bash
# List all workflows and jobs
act --list

# Run simple test workflow
act workflow_dispatch -W .github/workflows/simple-test.yml

# Run specific job from CI workflow
act push -W .github/workflows/ci.yml -j backend-tests

# Dry run to preview execution
act workflow_dispatch -W .github/workflows/local-test.yml -n

# Run with pull=false to use local Docker images
act workflow_dispatch -W .github/workflows/simple-test.yml --pull=false
```

### Test Results

✅ **Local testing confirmed working**:
- Python 3.10.12 available in containers
- System resources: 16 CPU cores, 31GB RAM
- Docker integration functional
- Workflow execution successful

## 🔧 Configuration Examples

### Adding Environment Variables

Edit `.env.local`:
```bash
# Add new environment variables
MY_API_KEY=test_value
DATABASE_PASSWORD=test_password
DEBUG=true
```

### Custom Workflow for Local Development

Create `.github/workflows/dev-test.yml`:
```yaml
name: Developer Test
on: workflow_dispatch

jobs:
  quick-test:
    runs-on: ubuntu-latest
    steps:
    - name: Run quick checks
      run: |
        echo "Running developer-specific tests..."
        # Add your custom test commands here
```

Run with: `act workflow_dispatch -W .github/workflows/dev-test.yml`

## 🐳 Docker Integration

### Container Images
- **Default**: `catthehacker/ubuntu:act-latest` (includes Node.js, Python, common tools)
- **Medium**: `catthehacker/ubuntu:act-20.04` (smaller, faster)
- **Full**: `catthehacker/ubuntu:full-20.04` (includes more tools, slower)

### Container Features
- **Volume Mounts**: Project directory mounted to `/github/workspace`
- **Network**: Host networking for service communication
- **Artifacts**: Stored in `./act-artifacts/` directory
- **Caching**: Tool cache and container reuse for speed

## 🚨 Troubleshooting

### Common Issues

#### GitHub Authentication Errors
```
authentication required: Invalid username or token
```
**Solution**: Add GitHub token to `.env.local`:
```bash
GITHUB_TOKEN=ghp_your_personal_access_token_here
```

#### Docker Permission Issues
```
permission denied while trying to connect to Docker daemon
```
**Solution**: 
- Ensure Docker Desktop is running
- Add user to `docker` group (Linux)
- Run with administrator privileges (Windows)

#### Container Pull Failures
```
Error: failed to pull image
```
**Solution**: Use `--pull=false` flag to use local images:
```bash
act workflow_dispatch -W .github/workflows/simple-test.yml --pull=false
```

#### Out of Space Errors
```
no space left on device
```
**Solution**: Clean up Docker resources:
```bash
# Using script
.\act-runner.ps1 -Clean

# Manual cleanup
docker container prune -f
docker image prune -f
docker volume prune -f
```

### Debug Mode

Enable verbose logging:
```bash
# With script
.\act-runner.ps1 -Workflow simple-test -Verbose

# Direct command
act workflow_dispatch -W .github/workflows/simple-test.yml --verbose
```

### Performance Optimization

1. **Container Reuse**: Add `--reuse` flag to `.actrc`
2. **Local Images**: Use `--pull=false` to avoid downloading
3. **Minimal Workflows**: Create lightweight test workflows for development
4. **Parallel Jobs**: Leverage multi-core systems for faster execution

## 📈 Monitoring and Metrics

### Coverage Reports
- **Backend**: pytest-cov generates XML reports for Codecov
- **Frontend**: Jest/Vitest coverage reports in LCOV format
- **Integration**: Combined coverage from all test suites

### Security Scans
- **Trivy**: Vulnerability scanning for dependencies and containers
- **Safety**: Python package vulnerability checking
- **Bandit**: Python security linting
- **SARIF**: Security reports uploaded to GitHub Security tab

### Performance Metrics
- **Build Time**: Tracked per workflow and job
- **Test Duration**: Individual test suite timing
- **Artifact Size**: Package sizes and optimization opportunities

## 🔄 Workflow Evolution

### Adding New Jobs

1. **Extend Existing Workflow**:
```yaml
jobs:
  existing-job:
    # ... existing configuration
    
  new-job:
    runs-on: ubuntu-latest
    needs: existing-job  # Optional dependency
    steps:
    - name: New step
      run: echo "New functionality"
```

2. **Test Locally**:
```bash
act workflow_dispatch -W .github/workflows/ci.yml -j new-job
```

3. **Deploy and Monitor**:
- Push to `develop` branch for staging testing
- Merge to `main` for production workflow activation

### Workflow Optimization

1. **Caching Strategy**:
```yaml
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

2. **Matrix Builds**:
```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11]
    node-version: [16, 18, 20]
```

3. **Conditional Execution**:
```yaml
- name: Run only on main branch
  if: github.ref == 'refs/heads/main'
  run: echo "Main branch specific command"
```

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [act GitHub Repository](https://github.com/nektos/act)
- [Docker Hub - GitHub Actions Runner Images](https://hub.docker.com/r/catthehacker/ubuntu)
- [Novel Engine Project Documentation](./README.md)

## 🤝 Contributing

When adding new workflows or modifying existing ones:

1. **Test Locally**: Always test with `act` before pushing
2. **Documentation**: Update this document with any changes
3. **Security**: Review security implications of new workflows
4. **Performance**: Consider impact on build times and resource usage
5. **Compatibility**: Ensure workflows work across different environments

---

*Last updated: August 12, 2025*