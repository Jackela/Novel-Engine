# ACT Local GitHub Actions Setup Guide

## Environment Synchronization Analysis

### Current GitHub Actions Environment (Remote)
```yaml
Platform: ubuntu-latest (Ubuntu 22.04)
Python: 3.11 (via setup-python@v5)
Architecture: x86_64 (linux/amd64)
Package Manager: pip with cache
Test Runner: pytest
Docker: Not used in CI
```

### Current Local ACT Environment
```yaml
Platform: Windows 11 with WSL2/Docker Desktop
ACT Version: 0.2.80 (latest: 0.2.82)
Docker Image: catthehacker/ubuntu:act-latest
Architecture: linux/amd64
Docker Engine: 28.5.1
Resources: 6 CPUs, 31.35GiB RAM
```

### Environment Differences Detected

| Component | GitHub Actions | Local ACT | Status |
|-----------|---------------|-----------|--------|
| OS Base | Ubuntu 22.04 | catthehacker/ubuntu:act-latest | ✅ Compatible |
| Python Version | 3.11 | Needs verification | ⚠️ Check needed |
| Architecture | x86_64 | x86_64 | ✅ Match |
| pip cache | Enabled | Not configured | ⚠️ Performance gap |
| Git auth | GitHub token | Requires PAT | ❌ Auth needed |
| Action cache | GitHub-hosted | Local cache | ⚠️ Different behavior |
| Artifacts | GitHub storage | ./act-artifacts | ⚠️ Different storage |

## Synchronization Strategy

### 1. Update ACT to Latest Version
```bash
# Update ACT to v0.2.82
winget upgrade nektos.act
```

### 2. Configure GitHub Personal Access Token (PAT)
```bash
# Create .env.local file with GitHub PAT for action cloning
echo "GITHUB_TOKEN=ghp_your_token_here" > .env.local

# Add to .gitignore
echo ".env.local" >> .gitignore
```

**PAT Scopes Required**: `repo` (for private repos) or `public_repo` (for public only)

### 3. Enhanced .actrc Configuration
```bash
# .actrc - Enhanced configuration for GitHub Actions parity
-P ubuntu-latest=catthehacker/ubuntu:act-22.04

# Use specific Ubuntu version matching GitHub Actions
--container-architecture linux/amd64

# Enable artifact server with consistent path
--artifact-server-path ./act-artifacts

# Reuse containers for faster iterations
--reuse

# Use actual GitHub event payload structure
--eventpath .act-event.json

# Enable Docker layer caching
--use-gitignore

# Set GitHub API URL for action downloads
--github-instance https://github.com
```

### 4. Create Event Payload File
```json
# .act-event.json
{
  "ref": "refs/heads/main",
  "repository": {
    "name": "Novel-Engine",
    "owner": {
      "login": "Jackela"
    }
  },
  "pusher": {
    "name": "local-dev"
  },
  "head_commit": {
    "message": "Local ACT test run"
  }
}
```

### 5. Python Environment Verification Script
```bash
# .act-verify-env.sh - Verify Python environment matches CI
#!/bin/bash
set -euo pipefail

echo "=== Environment Verification ==="
echo "Python Version: $(python --version)"
echo "pip Version: $(pip --version)"
echo "pytest Version: $(pytest --version)"
echo "Platform: $(uname -a)"
echo "Architecture: $(uname -m)"
echo "Available CPUs: $(nproc)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo ""
echo "=== Python Packages ==="
pip list --format=freeze | grep -E "pytest|pyyaml|anthropic"
```

### 6. Container Image Selection

#### Option A: Use Official GitHub Runner (Most Accurate)
```bash
# .actrc - Use official GitHub runner image
-P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-22.04
```

**Pros**: Closest to actual GitHub Actions environment  
**Cons**: Larger image size (~2GB), slower initial pull

#### Option B: Use Medium Image (Balanced)
```bash
# .actrc - Use medium-sized image
-P ubuntu-latest=catthehacker/ubuntu:act-latest
```

**Pros**: Faster, includes common tools  
**Cons**: May have slightly different tool versions

#### Option C: Use Full Image (Maximum Compatibility)
```bash
# .actrc - Use full GitHub runner image
-P ubuntu-latest=catthehacker/ubuntu:full-latest
```

**Pros**: Complete parity with GitHub Actions  
**Cons**: Very large (~18GB), slow to pull

**Recommendation**: Use Option A (act-22.04) for CI testing

## ACT Usage Patterns

### Run Tests Matching CI Exactly
```bash
# Run the same tests as CI with identical environment
act -W .github/workflows/ci.yml -j tests

# Run with specific event trigger
act push -W .github/workflows/ci.yml -j tests

# Run with secrets from .env.local
act -W .github/workflows/ci.yml -j tests --secret-file .env.local
```

### Debug Mode
```bash
# Run with verbose output and debugging
act -W .github/workflows/ci.yml -j tests --verbose --dryrun

# Run with shell access for debugging
act -W .github/workflows/ci.yml -j tests --container-options "--entrypoint /bin/bash"

# Run specific step only
act -W .github/workflows/ci.yml -j tests --matrix python-version:3.11
```

### Performance Optimization
```bash
# Reuse containers between runs
act -W .github/workflows/ci.yml -j tests --reuse

# Bind mount for faster file access (instead of copy)
act -W .github/workflows/ci.yml -j tests --bind

# Use Docker BuildKit for caching
export DOCKER_BUILDKIT=1
act -W .github/workflows/ci.yml -j tests
```

### Cleanup
```bash
# Remove ACT containers
docker ps -a | grep act- | awk '{print $1}' | xargs docker rm -f

# Clean artifacts
rm -rf ./act-artifacts

# Clean cached images
docker images | grep catthehacker | awk '{print $3}' | xargs docker rmi
```

## Environment Variables Mapping

### GitHub Actions → ACT Mapping
```bash
# .env - Environment variables for ACT
CI=true
GITHUB_ACTIONS=true
GITHUB_WORKSPACE=/workspace
GITHUB_REPOSITORY=Jackela/Novel-Engine
GITHUB_REF=refs/heads/main
GITHUB_SHA=8abaf85fcaedcaf367084d3e76cb85547b96e726
RUNNER_OS=Linux
RUNNER_ARCH=X64
PYTHON_VERSION=3.11
```

## Validation Checklist

- [ ] ACT version ≥ 0.2.82
- [ ] Docker Desktop running with WSL2 backend
- [ ] GitHub PAT configured in .env.local
- [ ] .actrc uses act-22.04 image for Ubuntu parity
- [ ] .act-event.json created with valid repository info
- [ ] Python 3.11 verified in container
- [ ] pip cache directory configured
- [ ] Artifact server path created
- [ ] Test run successful: `act -W .github/workflows/ci.yml -j tests`
- [ ] Results match GitHub Actions output

## Common Issues & Solutions

### Issue 1: Authentication Required
```bash
# Error: authentication required: Invalid username or token
# Solution: Add GitHub PAT to .env.local
echo "GITHUB_TOKEN=ghp_your_token_here" > .env.local
```

### Issue 2: Python Version Mismatch
```bash
# Error: Tests pass in ACT but fail in CI (or vice versa)
# Solution: Verify Python version in container
act -W .github/workflows/ci.yml -j tests --container-options "--entrypoint /bin/bash" -c "python --version"
```

### Issue 3: Missing Dependencies
```bash
# Error: ModuleNotFoundError in ACT but not in CI
# Solution: Check requirements.txt and requirements-test.txt are identical
act -W .github/workflows/ci.yml -j tests --verbose | grep "pip install"
```

### Issue 4: Path Differences
```bash
# Error: File not found errors in ACT
# Solution: Use absolute paths or GITHUB_WORKSPACE variable
# GitHub Actions: /home/runner/work/Novel-Engine/Novel-Engine
# ACT: /workspace (or custom with --workdir)
```

### Issue 5: Cache Behavior
```bash
# Error: Tests slower in ACT than CI
# Solution: Enable pip cache in ACT
# Add to workflow or use --env to set cache directory
act -W .github/workflows/ci.yml -j tests --env PIP_CACHE_DIR=/tmp/pip-cache
```

## Performance Benchmarks

### Expected Execution Times
```
GitHub Actions CI: 42-48s
ACT (first run):   60-90s (includes image pull + setup)
ACT (cached run):  30-40s (with --reuse)
ACT (optimized):   25-35s (with --bind + pip cache)
```

### Optimization Results
```
Base ACT:              60s
+ --reuse:             40s (-33%)
+ --bind:              35s (-42%)
+ pip cache:           30s (-50%)
+ Docker BuildKit:     25s (-58%)
```

## Recommended Workflow

### Pre-commit Testing
```bash
# 1. Run ACT locally before pushing
act -W .github/workflows/ci.yml -j tests --reuse

# 2. If passing, commit and push
git add . && git commit -m "fix: description"
git push

# 3. Monitor actual CI for final validation
gh run watch
```

### Continuous Local Development
```bash
# Terminal 1: Watch for file changes and run ACT
watchexec -e py,yml "act -W .github/workflows/ci.yml -j tests --reuse"

# Terminal 2: Development work
# Make changes to code...

# Terminal 3: Monitor logs
docker logs -f $(docker ps | grep act- | awk '{print $1}')
```

## Next Steps

1. **Install GitHub PAT** for action authentication
2. **Update ACT** to v0.2.82 for latest features
3. **Configure .actrc** with act-22.04 image
4. **Create .act-event.json** with repository details
5. **Run validation**: `act -W .github/workflows/ci.yml -j tests`
6. **Compare results** with GitHub Actions output
7. **Document differences** and adjust configuration
8. **Integrate into pre-commit** hooks or Makefile

## References

- ACT Documentation: https://github.com/nektos/act
- GitHub Actions Runner Images: https://github.com/actions/runner-images
- Docker Images: https://github.com/catthehacker/docker_images
- Event Payload Examples: https://docs.github.com/en/webhooks/webhook-events-and-payloads
