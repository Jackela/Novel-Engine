#!/bin/bash
# Bash script for running GitHub Actions locally with act
# Usage: ./act-runner.sh [options]

set -e

# Color functions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Default values
WORKFLOW=""
JOB=""
EVENT="push"
DRY_RUN=false
VERBOSE=false
LIST=false
CLEAN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        -j|--job)
            JOB="$2"
            shift 2
            ;;
        -e|--event)
            EVENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -l|--list)
            LIST=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -w, --workflow NAME    Run specific workflow"
            echo "  -j, --job NAME         Run specific job"
            echo "  -e, --event EVENT      Trigger event (default: push)"
            echo "      --dry-run          Show what would be run"
            echo "  -v, --verbose          Verbose output"
            echo "  -l, --list             List available workflows"
            echo "      --clean            Clean up Docker resources"
            echo "  -h, --help             Show this help"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

info "Novel Engine - Local GitHub Actions Runner (act)"
info "=============================================="

# Check if act is installed
if ! command -v act &> /dev/null; then
    error "act is not installed or not in PATH"
    info "Install from: https://github.com/nektos/act"
    exit 1
fi

# Check Docker
if ! docker info &> /dev/null; then
    error "Docker is not running"
    exit 1
fi

# Clean up containers if requested
if [ "$CLEAN" = true ]; then
    info "Cleaning up Docker containers and images..."
    docker container prune -f
    docker image prune -f
    success "Cleanup complete"
fi

# List available workflows and jobs
if [ "$LIST" = true ]; then
    info "Available workflows:"
    act --list
    exit 0
fi

# Create artifacts directory
mkdir -p act-artifacts
info "Artifacts will be stored in: act-artifacts/"

# Ensure .env.local exists
if [ ! -f ".env.local" ]; then
    cp ".env.local" ".env.local.example" 2>/dev/null || true
    warning ".env.local not found. Please create and configure it."
fi

# Build act command
ACT_CMD="act $EVENT"

# Add workflow if specified
if [ -n "$WORKFLOW" ]; then
    ACT_CMD="$ACT_CMD -W .github/workflows/$WORKFLOW.yml"
fi

# Add job if specified
if [ -n "$JOB" ]; then
    ACT_CMD="$ACT_CMD -j $JOB"
fi

# Add flags
if [ "$VERBOSE" = true ]; then
    ACT_CMD="$ACT_CMD --verbose"
fi

if [ "$DRY_RUN" = true ]; then
    ACT_CMD="$ACT_CMD --dry-run"
fi

# Common useful flags
ACT_CMD="$ACT_CMD --secret-file .env.local"
ACT_CMD="$ACT_CMD --artifact-server-path ./act-artifacts"
ACT_CMD="$ACT_CMD --container-architecture linux/amd64"

info "Running command: $ACT_CMD"
echo

# Execute act command
if eval $ACT_CMD; then
    success "Workflow execution completed successfully!"
    if [ -d "act-artifacts" ]; then
        info "Artifacts saved to: act-artifacts/"
    fi
else
    error "Workflow execution failed"
    info "Try running with --verbose for more details"
    exit 1
fi

echo
info "Quick commands:"
info "  List workflows:     $0 --list"
info "  Run specific job:   $0 -w ci -j backend-tests"
info "  Local test:         $0 -w local-test"
info "  Dry run:           $0 -w ci --dry-run"
info "  Clean up:          $0 --clean"