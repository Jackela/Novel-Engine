# GitHub Actions Configuration

This directory contains the CI/CD workflows for the Novel Engine project.

## 📁 Workflows

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI Pipeline** | `ci.yml` | Push/PR to main, develop | Testing, linting, security, build |
| **Staging Deploy** | `deploy-staging.yml` | Push to develop | Automated staging deployment |
| **Production Release** | `release.yml` | Git tags (v*) | Release management |
| **Local Test** | `local-test.yml` | Manual/Push | Optimized for local `act` testing |
| **Simple Test** | `simple-test.yml` | Manual | Basic environment validation |

## 🚀 Quick Start

### Local Testing with act

1. **Install act** (if not already installed):
   ```bash
   # Windows
   winget install nektos.act
   
   # macOS
   brew install act
   
   # Linux
   curl -sL https://raw.githubusercontent.com/nektos/act/master/install.sh | bash
   ```

2. **Configure environment**:
   ```bash
   # Copy and edit environment file
   cp .env.local .env.local.example
   # Edit .env.local with your settings
   ```

3. **Run workflows locally**:
   ```bash
   # List all workflows
   act --list
   
   # Run simple test
   act workflow_dispatch -W .github/workflows/simple-test.yml
   
   # Run CI backend tests
   act push -W .github/workflows/ci.yml -j backend-tests
   ```

### Using Helper Scripts

**PowerShell** (Windows):
```powershell
# List workflows
.\act-runner.ps1 -List

# Run simple test
.\act-runner.ps1 -Workflow simple-test

# Run with verbose output
.\act-runner.ps1 -Workflow local-test -Verbose
```

**Bash** (Linux/macOS):
```bash
# Make executable
chmod +x act-runner.sh

# Run workflows
./act-runner.sh --list
./act-runner.sh -w simple-test
```

## 📋 Workflow Details

### CI Pipeline (`ci.yml`)

**Jobs**:
- `backend-tests` - Python testing, linting, coverage
- `frontend-tests` - Node.js testing, TypeScript checking
- `e2e-tests` - Playwright integration testing
- `security` - Vulnerability scanning
- `build` - Package creation and artifacts

**Features**:
- ✅ Parallel execution
- 📊 Coverage reporting to Codecov
- 🛡️ Security scanning (Trivy, Safety, Bandit)
- 📦 Build artifacts generation

### Staging Deployment (`deploy-staging.yml`)

**Triggers**: Push to `develop` branch

**Features**:
- 🏥 Health checks before deployment
- 🚀 Automated staging deployment
- 🔄 Rollback capability
- 💪 Force deployment option

### Production Release (`release.yml`)

**Triggers**: Git tags matching `v*` pattern

**Features**:
- 📝 Automated changelog generation
- 🎯 GitHub release creation
- 🔒 Manual approval for production
- 📊 Full test suite validation

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `.actrc` | act configuration and preferences |
| `.env.local` | Local environment variables for testing |
| `act-runner.ps1` | PowerShell helper script |
| `act-runner.sh` | Bash helper script |

## 🐳 Docker Integration

The workflows use `catthehacker/ubuntu:act-latest` containers which include:
- Python 3.10+
- Node.js 18+
- Docker
- Common development tools

## 📚 Documentation

See [docs/GITHUB_ACTIONS.md](../docs/GITHUB_ACTIONS.md) for detailed documentation including:
- Complete setup instructions
- Troubleshooting guide
- Performance optimization
- Security configuration
- Advanced usage examples

## 🚨 Troubleshooting

### Common Issues

**Authentication Error**:
```bash
# Add GitHub token to .env.local
GITHUB_TOKEN=your_personal_access_token
```

**Docker Issues**:
```bash
# Use local images to avoid pulls
act --pull=false

# Clean up resources
docker system prune -f
```

**Permission Errors**:
- Ensure Docker Desktop is running
- Run with appropriate permissions
- Check file permissions on scripts

## 🤝 Contributing

1. **Test Locally**: Use `act` to test workflows before pushing
2. **Follow Conventions**: Maintain consistent naming and structure
3. **Document Changes**: Update this README and main documentation
4. **Security Review**: Ensure no secrets are exposed in workflows

## 📞 Support

- 📖 [Full Documentation](../docs/GITHUB_ACTIONS.md)
- 🐛 [GitHub Issues](https://github.com/Jackela/Novel-Engine/issues)
- 💬 [Project Discussions](https://github.com/Jackela/Novel-Engine/discussions)

---

*For detailed information, see the complete [GitHub Actions Documentation](../docs/GITHUB_ACTIONS.md).*