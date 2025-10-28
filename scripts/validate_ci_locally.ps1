# CI/CD Local Validation Script (PowerShell)
# Purpose: Run exact same tests and coverage checks as GitHub Actions Quality Assurance Pipeline
# Usage: .\scripts\validate_ci_locally.ps1

$ErrorActionPreference = 'Stop'

Write-Host "🔍 CI/CD Local Validation for Novel-Engine" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version (must be 3.11)
Write-Host "📋 Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = (python --version 2>&1) -replace 'Python ', ''
    if (-not ($pythonVersion -match '^3\.11')) {
        Write-Host "❌ Python 3.11 required for local validation" -ForegroundColor Red
        Write-Host "   Found: Python $pythonVersion" -ForegroundColor Yellow
        Write-Host "   Install: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✓ Python $pythonVersion detected" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "   Install Python 3.11: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pytest pytest-cov coverage httpx pytest-timeout pytest-asyncio --quiet
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Run exact CI commands (matching GitHub Actions quality_assurance.yml test-suite job)
Write-Host "🧪 Running tests with coverage (this matches GitHub Actions exactly)..." -ForegroundColor Yellow
Write-Host ""

$testExitCode = 0
try {
    python -m pytest `
      --cov=src `
      --cov-config=.coveragerc `
      --cov-report=xml `
      --cov-report=html `
      --cov-report=term-missing `
      --junitxml=test-results.xml `
      --maxfail=10 `
      -v `
      --tb=short `
      --durations=10
    
    $testExitCode = $LASTEXITCODE
}
catch {
    $testExitCode = 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if ($testExitCode -eq 0) {
    Write-Host "✅ Validation PASSED" -ForegroundColor Green
    Write-Host "   All tests passed and coverage meets 30% threshold" -ForegroundColor Green
    Write-Host "   Safe to push to GitHub" -ForegroundColor Green
}
else {
    Write-Host "❌ Validation FAILED" -ForegroundColor Red
    Write-Host "   Fix issues before pushing to GitHub" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Test failures: Check test output above for failing tests" -ForegroundColor Yellow
    Write-Host "  - Coverage below 30%: Add tests or check .coveragerc configuration" -ForegroundColor Yellow
    Write-Host "  - Import errors: Verify PYTHONPATH includes src/" -ForegroundColor Yellow
}
Write-Host "==========================================" -ForegroundColor Cyan

exit $testExitCode
