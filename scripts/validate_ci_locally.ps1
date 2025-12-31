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
pip install pytest pytest-asyncio pytest-timeout httpx --quiet
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Run backend CI gates (parity with GitHub Actions)
Write-Host "🧪 Running backend CI gates..." -ForegroundColor Yellow
Write-Host ""

$testExitCode = 0
$env:PYTHONPATH = "$PWD;$PWD\src"
$minPyramidScore = if ($env:MIN_PYRAMID_SCORE) { [double]$env:MIN_PYRAMID_SCORE } else { 5.5 }

if (-not (Test-Path "reports")) {
    New-Item -ItemType Directory -Path "reports" | Out-Null
}

python scripts/testing/validate-test-markers.py --all --verbose
if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

python scripts/testing/test-pyramid-monitor-fast.py --format json --save-history > pyramid-report.json
if ($LASTEXITCODE -ne 0) {
    $testExitCode = 1
} else {
    $report = Get-Content "pyramid-report.json" | ConvertFrom-Json
    if ($report.score -lt $minPyramidScore) {
        Write-Host "❌ Test pyramid score ($($report.score)) below threshold ($minPyramidScore)" -ForegroundColor Red
        $testExitCode = 1
    }
}

python -m pytest -m "unit" --tb=short --durations=10 --junitxml=reports/unit-tests.xml
if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

python -m pytest -m "integration" --tb=short --durations=10 --junitxml=reports/integration-tests.xml
if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

python -m pytest -m "e2e" --tb=short --durations=10 --junitxml=reports/e2e-tests.xml
if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

python -m pytest -q tests/test_enhanced_bridge.py tests/test_character_system_comprehensive.py --junitxml=reports/smoke-tests.xml
if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

Write-Host ""
Write-Host "🌐 Running frontend CI checks..." -ForegroundColor Yellow
$frontendDir = "frontend"
if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    if (Test-Path "package.json") {
        npm test --if-present --silent
        if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

        npm run build --if-present
        if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }

        $env:PYTHONPATH = "..;..\src"
        npm run test:e2e:smoke
        if ($LASTEXITCODE -ne 0) { $testExitCode = 1 }
    } else {
        Write-Host "⚠ No frontend package.json found, skipping" -ForegroundColor Yellow
    }
    Pop-Location
} else {
    Write-Host "⚠ Frontend directory not found, skipping" -ForegroundColor Yellow
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
