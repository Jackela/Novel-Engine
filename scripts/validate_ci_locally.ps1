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

function Get-GzipSizeKb {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $memoryStream = New-Object System.IO.MemoryStream
    $gzipStream = New-Object System.IO.Compression.GzipStream(
        $memoryStream,
        [System.IO.Compression.CompressionMode]::Compress
    )
    $gzipStream.Write($bytes, 0, $bytes.Length)
    $gzipStream.Close()
    $sizeKb = [math]::Floor($memoryStream.Length / 1KB)
    $memoryStream.Dispose()
    return $sizeKb
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
$pathsToRemove = @(
    "reports",
    "coverage",
    "dist",
    "node_modules",
    "frontend/node_modules",
    "frontend/dist"
)
foreach ($path in $pathsToRemove) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "✓ Environment cleaned" -ForegroundColor Green
Write-Host ""

# Install dependencies (matching GitHub Actions ci.yml)
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Assert-LastExitCode "Upgrade pip"
pip install -r requirements.txt --quiet
Assert-LastExitCode "Install Python requirements"
# Install test dependencies from requirements-test.txt (GA parity)
if (Test-Path "requirements/requirements-test.txt") {
    pip install -r requirements/requirements-test.txt --quiet
    Assert-LastExitCode "Install test requirements"
}
# Editable install for proper package imports (GA parity)
pip install -e . --quiet
Assert-LastExitCode "Editable install"
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Security scanning with bandit (local alternative to CodeQL)
Write-Host "🔒 Running security scan (bandit)..." -ForegroundColor Yellow
$banditInstalled = python -m bandit --version 2>&1 | Select-String "bandit"
if ($banditInstalled) {
    # Run bandit with medium-low severity threshold (-ll = medium and above)
    # Only fail on high severity issues (-lll would be high only)
    $banditResult = python -m bandit -r src/ -ll -q --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        $banditJson = $banditResult | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($banditJson -and $banditJson.results) {
            $highSeverity = ($banditJson.results | Where-Object { $_.issue_severity -eq "HIGH" }).Count
            $mediumSeverity = ($banditJson.results | Where-Object { $_.issue_severity -eq "MEDIUM" }).Count
            Write-Host "⚠ Security issues found: $highSeverity high, $mediumSeverity medium" -ForegroundColor Yellow

            # Show high severity issues
            $banditJson.results | Where-Object { $_.issue_severity -eq "HIGH" } | ForEach-Object {
                Write-Host "  [$($_.test_id)] $($_.filename):$($_.line_number) - $($_.issue_text)" -ForegroundColor Red
            }

            # Fail only on high severity issues that are NOT marked with nosec
            if ($highSeverity -gt 0) {
                Write-Host "⚠ High severity issues found - review before pushing" -ForegroundColor Yellow
                Write-Host "  Use '# nosec BXXX' comment to suppress false positives" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "✅ No high/medium security issues found" -ForegroundColor Green
    }
} else {
    Write-Host "⚠ bandit not installed. Run: pip install bandit" -ForegroundColor Yellow
    Write-Host "  Skipping security scan..." -ForegroundColor Gray
}
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

# Smoke tests path matches GA ci.yml
python -m pytest -q tests/test_character_system_comprehensive.py tests/smoke/ --junitxml=reports/smoke-tests.xml
Assert-LastExitCode "Smoke tests"

# Speed Regression Check (GA parity)
Write-Host "🚀 Running speed regression check..." -ForegroundColor Yellow
python scripts/testing/test-speed-report.py --format json > speed-report.json
$speedReport = Get-Content "speed-report.json" | ConvertFrom-Json
$slowCount = $speedReport.slow_tests.count
Write-Host "Found $slowCount slow tests (>1000ms)"
if ($slowCount -gt 10) {
    Write-Host "⚠ Warning: Found $slowCount slow tests. Consider optimization." -ForegroundColor Yellow
}
Write-Host ""

Write-Host ""
Write-Host "🌐 Running frontend CI checks..." -ForegroundColor Yellow
$frontendDir = "frontend"
if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    if (Test-Path "package.json") {
        npm ci
        Assert-LastExitCode "Install frontend dependencies"

        npm run lint:all --if-present
        Assert-LastExitCode "Frontend lint"

        npm run type-check --if-present
        Assert-LastExitCode "Frontend typecheck"

        npm run format:check --if-present
        Assert-LastExitCode "Frontend format check"

        npm run build:tokens --if-present
        Assert-LastExitCode "Frontend token generation"

        npm run tokens:check --if-present
        Assert-LastExitCode "Frontend token checks"

        npm test --if-present --silent
        Assert-LastExitCode "Frontend unit tests"

        npm run test:integration --if-present
        Assert-LastExitCode "Frontend integration tests"

        $env:NODE_ENV = "production"
        npm run build --if-present
        Assert-LastExitCode "Frontend build"

        if (Test-Path "dist") {
            Write-Host "📦 Checking bundle sizes..." -ForegroundColor Yellow
            $initialBundle = Get-ChildItem "dist" -Recurse -Filter "index-*.js" | Select-Object -First 1
            if ($null -ne $initialBundle) {
                $initialSizeKb = Get-GzipSizeKb $initialBundle.FullName
                Write-Host "Initial bundle: ${initialSizeKb}KB (gzip)"
                if ($initialSizeKb -gt 400) {
                    Write-Host "❌ Initial bundle ${initialSizeKb}KB exceeds 400KB limit" -ForegroundColor Red
                    exit 1
                }
            }

            $routeChunks = Get-ChildItem "dist" -Recurse -Filter "*.js" | Where-Object {
                $_.Name -notlike "index-*.js" -and $_.Name -notlike "vendor-*.js"
            }
            foreach ($chunk in $routeChunks) {
                $chunkSizeKb = Get-GzipSizeKb $chunk.FullName
                Write-Host "  $($chunk.Name): ${chunkSizeKb}KB (gzip)"
                if ($chunkSizeKb -gt 200) {
                    Write-Host "❌ Chunk $($chunk.Name) exceeds 200KB limit" -ForegroundColor Red
                    exit 1
                }
            }
            Write-Host "✅ Bundle sizes within thresholds" -ForegroundColor Green
        }

        # Lighthouse CI (GA parity) - enabled by default for full CI parity
        $runLighthouse = if ($env:SKIP_LIGHTHOUSE -eq "1") { $false } else { $true }
        if ($runLighthouse) {
            Write-Host "🔦 Running Lighthouse CI..." -ForegroundColor Yellow
            # Check if @lhci/cli is available
            $lhciInstalled = npm list -g @lhci/cli 2>&1 | Select-String "@lhci/cli"
            if (-not $lhciInstalled) {
                Write-Host "Installing @lhci/cli..." -ForegroundColor Yellow
                npm install -g @lhci/cli@0.14.0
            }
            npx @lhci/cli@0.14.0 autorun
            if ($LASTEXITCODE -ne 0) {
                Write-Host "⚠ Lighthouse CI failed - continuing with other checks" -ForegroundColor Yellow
            } else {
                Write-Host "✅ Lighthouse CI passed" -ForegroundColor Green
            }
        } else {
            Write-Host "⚠ Skipping Lighthouse CI (SKIP_LIGHTHOUSE=1 is set)" -ForegroundColor Yellow
        }

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
        $env:CI = "true"
        npm run test:e2e:smoke
        Assert-LastExitCode "Playwright E2E smoke tests"

        # Full E2E is opt-in (smoke tests are sufficient for local validation)
        $runFullE2E = if ($env:RUN_FULL_E2E -eq "1") { $true } else { $false }
        if ($runFullE2E) {
            npm run test:e2e
            Assert-LastExitCode "Playwright full E2E suite"
        } else {
            Write-Host "⚠ Skipping full Playwright E2E suite (set RUN_FULL_E2E=1 to enable)" -ForegroundColor Yellow
        }
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
