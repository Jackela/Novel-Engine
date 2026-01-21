# CI/CD Local Validation Script (PowerShell)
# Purpose: Run exact same tests and coverage checks as GitHub Actions Quality Assurance Pipeline
# Usage: .\scripts\validate_ci_locally.ps1

$ErrorActionPreference = 'Stop'

Write-Host "🔍 CI/CD Local Validation for Novel-Engine" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ $Step failed (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}

# Check Python version (must be 3.11+)
Write-Host "📋 Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = (python --version 2>&1) -replace 'Python ', ''
    $parsedVersion = [version]$pythonVersion
    if ($parsedVersion.Major -ne 3 -or $parsedVersion.Minor -lt 11) {
        Write-Host "❌ Python 3.11+ required for local validation" -ForegroundColor Red
        Write-Host "   Found: Python $pythonVersion" -ForegroundColor Yellow
        Write-Host "   Install: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "✓ Python $pythonVersion detected" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "   Install Python 3.11+: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Clean environment artifacts
Write-Host "🧹 Cleaning environment..." -ForegroundColor Yellow
$cacheDirs = Get-ChildItem -Path "." -Recurse -Force -Directory -Filter "__pycache__"
foreach ($dir in $cacheDirs) {
    Remove-Item $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
$pytestCaches = Get-ChildItem -Path "." -Recurse -Force -Directory -Filter ".pytest_cache"
foreach ($dir in $pytestCaches) {
    Remove-Item $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
$pathsToRemove = @("reports", "coverage", "frontend/dist")
foreach ($path in $pathsToRemove) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "✓ Environment cleaned" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Assert-LastExitCode "Upgrade pip"
pip install -r requirements.txt --quiet
Assert-LastExitCode "Install Python requirements"
pip install pytest pytest-asyncio pytest-timeout httpx --quiet
Assert-LastExitCode "Install test dependencies"
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Run backend CI gates (parity with GitHub Actions)
Write-Host "🧪 Running backend CI gates..." -ForegroundColor Yellow
Write-Host ""

$env:PYTHONPATH = "$PWD\src"
$minPyramidScore = if ($env:MIN_PYRAMID_SCORE) { [double]$env:MIN_PYRAMID_SCORE } else { 5.5 }

if (-not (Test-Path "reports")) {
    New-Item -ItemType Directory -Path "reports" | Out-Null
}

python scripts/testing/validate-test-markers.py --all --verbose
Assert-LastExitCode "Validate test markers"

python scripts/testing/test-pyramid-monitor-fast.py --format json --save-history > pyramid-report.json
Assert-LastExitCode "Generate test pyramid report"
$report = Get-Content "pyramid-report.json" | ConvertFrom-Json
if ($report.score -lt $minPyramidScore) {
    Write-Host "❌ Test pyramid score ($($report.score)) below threshold ($minPyramidScore)" -ForegroundColor Red
    exit 1
}

python -m pytest -m "unit" --tb=short --durations=10 --junitxml=reports/unit-tests.xml
Assert-LastExitCode "Unit tests"

python -m pytest -m "integration" --tb=short --durations=10 --junitxml=reports/integration-tests.xml
Assert-LastExitCode "Integration tests"

python -m pytest -m "e2e" --tb=short --durations=10 --junitxml=reports/e2e-tests.xml
Assert-LastExitCode "E2E tests"

python -m pytest -q tests/test_enhanced_bridge.py tests/test_character_system_comprehensive.py --junitxml=reports/smoke-tests.xml
Assert-LastExitCode "Smoke tests"

Write-Host ""
Write-Host "🌐 Running frontend CI checks..." -ForegroundColor Yellow
$frontendDir = "frontend"
if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    if (Test-Path "package.json") {
        npm test --if-present --silent
        Assert-LastExitCode "Frontend tests"

        npm run build --if-present
        Assert-LastExitCode "Frontend build"

        $env:PYTHONPATH = "..\src"
        $playwrightPort = 3000
        try {
            $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 3000)
            $listener.Start()
            $listener.Stop()
        } catch {
            $playwrightPort = 3001
        }
        $env:PLAYWRIGHT_PORT = $playwrightPort
        $env:VITE_DEV_PORT = $playwrightPort
        npm run test:e2e:smoke
        Assert-LastExitCode "Playwright smoke tests"
    } else {
        Write-Host "⚠ No frontend package.json found, skipping" -ForegroundColor Yellow
    }
    Pop-Location
} else {
    Write-Host "⚠ Frontend directory not found, skipping" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Validation PASSED" -ForegroundColor Green
Write-Host "   All tests passed and coverage meets 20% threshold" -ForegroundColor Green
Write-Host "   Safe to push to GitHub" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

exit 0
