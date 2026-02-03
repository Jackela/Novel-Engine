#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run CodeQL security analysis locally before pushing.

.DESCRIPTION
    This script runs CodeQL analysis on Python and JavaScript code
    to catch security issues before they reach CI.

.EXAMPLE
    .\scripts\codeql-local.ps1
    .\scripts\codeql-local.ps1 -Language python
    .\scripts\codeql-local.ps1 -QuickScan
#>

param(
    [ValidateSet("python", "javascript", "all")]
    [string]$Language = "all",
    [switch]$QuickScan,
    [switch]$RequireCodeQL,
    [switch]$Help
)

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $ProjectRoot) { $ProjectRoot = Get-Location }

Write-Host "=== CodeQL Local Security Scan ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

# Check if CodeQL is installed
$codeqlPath = Get-Command codeql -ErrorAction SilentlyContinue
if (-not $codeqlPath) {
    if ($RequireCodeQL) {
        Write-Host "`nCodeQL CLI is required for this scan but was not found." -ForegroundColor Red
        Write-Host "Install CodeQL and re-run the scan." -ForegroundColor Yellow
        exit 1
    }
    Write-Host @"

CodeQL CLI not found. Install options:

1. Using scoop (recommended for Windows):
   scoop install codeql

2. Manual download:
   https://github.com/github/codeql-cli-binaries/releases

3. Alternative: Use the Python linters for quick checks:
   pip install bandit safety
   bandit -r src/ -ll
   safety check

"@ -ForegroundColor Yellow

    Write-Host "Running alternative security checks with bandit..." -ForegroundColor Cyan

    # Run bandit as alternative
    if (Get-Command bandit -ErrorAction SilentlyContinue) {
        Write-Host "`n=== Bandit Security Scan ===" -ForegroundColor Cyan
        bandit -r src/ -ll --format txt
        if ($LASTEXITCODE -ne 0) {
            exit 1
        }
    } else {
        Write-Host "bandit not installed. Run: pip install bandit" -ForegroundColor Yellow
    }

    exit 0
}

Write-Host "CodeQL found: $($codeqlPath.Source)" -ForegroundColor Green

# Create temporary database directory
$dbDir = Join-Path $env:TEMP "codeql-db-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
$issuesFound = $false

try {
    $languages = @()
    if ($Language -eq "all") {
        $languages = @("python", "javascript")
    } else {
        $languages = @($Language)
    }

    foreach ($lang in $languages) {
        Write-Host "`n=== Scanning $lang ===" -ForegroundColor Cyan

        $langDbDir = Join-Path $dbDir $lang

        # Create database
        Write-Host "Creating CodeQL database for $lang..."
        if ($lang -eq "python") {
            codeql database create $langDbDir --language=$lang --source-root=$ProjectRoot --overwrite 2>&1
        } else {
            Push-Location (Join-Path $ProjectRoot "frontend")
            codeql database create $langDbDir --language=$lang --source-root=. --overwrite 2>&1
            Pop-Location
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Warning: Database creation had issues, continuing..." -ForegroundColor Yellow
        }

        # Run analysis
        Write-Host "Running security analysis..."
        $resultsFile = Join-Path $dbDir "$lang-results.sarif"

        $queryPack = if ($QuickScan) {
            "codeql/$lang-queries:codeql-suites/$lang-security-extended.qls"
        } else {
            "codeql/$lang-queries"
        }

        codeql database analyze $langDbDir $queryPack --format=sarifv2.1.0 --output=$resultsFile 2>&1

        if (Test-Path $resultsFile) {
            Write-Host "`nResults saved to: $resultsFile" -ForegroundColor Green

            # Parse and display results
            $sarif = Get-Content $resultsFile | ConvertFrom-Json
            $results = $sarif.runs[0].results

            if ($results.Count -eq 0) {
                Write-Host "No security issues found!" -ForegroundColor Green
            } else {
                $issuesFound = $true
                Write-Host "`nFound $($results.Count) issues:" -ForegroundColor Yellow
                foreach ($result in $results) {
                    $ruleId = $result.ruleId
                    $message = $result.message.text
                    $location = $result.locations[0].physicalLocation
                    $file = $location.artifactLocation.uri
                    $line = $location.region.startLine

                    Write-Host "  [$ruleId] $file`:$line" -ForegroundColor Red
                    Write-Host "    $message" -ForegroundColor Gray
                }
            }
        }
    }

    Write-Host "`n=== Scan Complete ===" -ForegroundColor Cyan
} finally {
    # Cleanup
    if (Test-Path $dbDir) {
        Remove-Item -Recurse -Force $dbDir -ErrorAction SilentlyContinue
    }
}

if ($issuesFound) {
    exit 1
}

exit 0
