# PowerShell script for running GitHub Actions locally with act
# Usage: .\act-runner.ps1 [workflow] [job] [options]

param(
    [string]$Workflow = "",
    [string]$Job = "",
    [string]$Event = "push",
    [switch]$DryRun = $false,
    [switch]$Verbose = $false,
    [switch]$List = $false,
    [switch]$Clean = $false
)

# Color functions for output
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Blue }

Write-Info "Novel Engine - Local GitHub Actions Runner (act)"
Write-Info "=============================================="

# Check if act is installed
if (-not (Get-Command "act" -ErrorAction SilentlyContinue)) {
    Write-Error "act is not installed or not in PATH"
    Write-Info "Install with: winget install nektos.act"
    exit 1
}

# Clean up containers if requested
if ($Clean) {
    Write-Info "Cleaning up Docker containers and images..."
    docker container prune -f
    docker image prune -f
    Write-Success "Cleanup complete"
}

# List available workflows and jobs
if ($List) {
    Write-Info "Available workflows:"
    act --list
    exit 0
}

# Create artifacts directory
if (-not (Test-Path "act-artifacts")) {
    New-Item -ItemType Directory -Path "act-artifacts" | Out-Null
    Write-Info "Created act-artifacts directory"
}

# Ensure .env.local exists
if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.local" ".env.local.example" -ErrorAction SilentlyContinue
    Write-Warning ".env.local not found. Created example file - please configure it."
}

# Build act command
$actCommand = @("act")

# Add event
$actCommand += $Event

# Add workflow if specified
if ($Workflow) {
    $actCommand += "-W", ".github/workflows/$Workflow.yml"
}

# Add job if specified
if ($Job) {
    $actCommand += "-j", $Job
}

# Add verbose flag if requested
if ($Verbose) {
    $actCommand += "--verbose"
}

# Add dry run flag if requested
if ($DryRun) {
    $actCommand += "--dry-run"
}

# Common useful flags
$actCommand += "--secret-file", ".env.local"
$actCommand += "--artifact-server-path", "./act-artifacts"
$actCommand += "--container-architecture", "linux/amd64"

Write-Info "Running command: $($actCommand -join ' ')"
Write-Info ""

# Execute act command
& $actCommand[0] $actCommand[1..$actCommand.Length]

if ($LASTEXITCODE -eq 0) {
    Write-Success "Workflow execution completed successfully!"
    if (Test-Path "act-artifacts") {
        Write-Info "Artifacts saved to: act-artifacts/"
    }
} else {
    Write-Error "Workflow execution failed (exit code: $LASTEXITCODE)"
    Write-Info "Try running with -Verbose for more details"
}

Write-Info ""
Write-Info "Quick commands:"
Write-Info "  List workflows:     .\act-runner.ps1 -List"
Write-Info "  Run specific job:   .\act-runner.ps1 -Workflow ci -Job backend-tests"
Write-Info "  Local test:         .\act-runner.ps1 -Workflow local-test"
Write-Info "  Dry run:           .\act-runner.ps1 -Workflow ci -DryRun"
Write-Info "  Clean up:          .\act-runner.ps1 -Clean"