#!/usr/bin/env bash
#
# ci-local.sh - Local CI verification script that simulates GitHub Actions environment
#
# This script replicates the CI environment locally to catch issues before pushing.
# It runs the same commands as GitHub Actions to ensure local/CI parity.
#
# Usage:
#   ./scripts/ci-local.sh           # Full CI simulation (Python tests + quality checks)
#   ./scripts/ci-local.sh --python  # Python tests only (matches python-tests.yml)
#   ./scripts/ci-local.sh --quality # Quality checks only (ruff, mypy, bandit)
#   ./scripts/ci-local.sh --help    # Show help
#
# Environment:
#   This script automatically sources .env.ci to match CI environment variables.
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#

set -o pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
MIN_COVERAGE=70
PYTHON_VERSION="3.11"

# Source CI environment variables
if [ -f "$PROJECT_ROOT/.env.ci" ]; then
    source "$PROJECT_ROOT/.env.ci"
fi

# Ensure CI environment variables are set
export CI=true
export GITHUB_ACTIONS=true
export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/src:${PYTHONPATH:-}"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Track results
FAILED=0
TOTAL_CHECKS=0

# Run a check with error handling
run_check() {
    local name="$1"
    local command="$2"
    
    ((TOTAL_CHECKS++))
    print_info "Running: $name..."
    
    if eval "$command"; then
        print_success "$name passed"
        return 0
    else
        print_error "$name failed"
        ((FAILED++))
        return 1
    fi
}

# ==================== PYTHON TESTS (matches python-tests.yml) ====================

run_python_tests() {
    print_header "PYTHON TESTS (matching python-tests.yml)"
    
    # Verify Python version
    LOCAL_PYTHON=$(python3 --version 2>&1 | head -1)
    print_info "Python version: $LOCAL_PYTHON"
    if [[ ! "$LOCAL_PYTHON" =~ "$PYTHON_VERSION" ]]; then
        print_warning "Python version mismatch - CI uses Python $PYTHON_VERSION"
    fi
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    
    # Install dependencies (matches CI step)
    print_info "Installing dependencies..."
    python -m pip install --upgrade pip -q
    pip install -q -r "$PROJECT_ROOT/requirements.txt"
    pip install -q -r "$PROJECT_ROOT/requirements/requirements-test.txt"
    pip install -q -e "$PROJECT_ROOT"
    
    # Run tests with coverage (matches CI exactly)
    print_info "Running Python tests with coverage..."
    if pytest tests/ \
        --cov=src \
        --cov-report=xml \
        --cov-report=term \
        --cov-fail-under=$MIN_COVERAGE \
        --tb=short \
        -v; then
        print_success "Python tests passed"
    else
        print_error "Python tests failed"
        ((FAILED++))
    fi
    
    # Check coverage file was created
    if [ -f "$PROJECT_ROOT/coverage.xml" ]; then
        print_info "Coverage report: coverage.xml"
    fi
}

# ==================== QUALITY CHECKS (matches python-tests.yml) ====================

run_quality_checks() {
    print_header "QUALITY CHECKS (matching python-tests.yml)"
    
    # Install quality tools
    print_info "Installing quality tools..."
    pip install -q mypy ruff bandit
    
    # Ruff linter (matches CI: ruff check src/ tests/ --output-format=github)
    run_check "Ruff Linter" "ruff check src/ tests/ --output-format=github 2>&1 | head -50" || true
    
    # MyPy type checker (matches CI: mypy src/ --no-error-summary --show-column-numbers)
    run_check "MyPy Type Checker" "mypy src/ --no-error-summary --show-column-numbers 2>&1 | head -50" || true
    
    # Bandit security scan (matches CI: bandit -r src/ -ll -ii)
    print_info "Running Bandit security scan..."
    if bandit -r src/ -ll -ii -f json -o "$REPORTS_DIR/bandit-report.json" 2>/dev/null; then
        print_success "Bandit scan completed (see $REPORTS_DIR/bandit-report.json)"
    else
        print_warning "Bandit found issues (see $REPORTS_DIR/bandit-report.json)"
    fi
    
    # Show bandit summary
    if [ -f "$REPORTS_DIR/bandit-report.json" ]; then
        local high_severity=$(python -c "import json; data=json.load(open('$REPORTS_DIR/bandit-report.json')); print(len([r for r in data.get('results', []) if r['issue_severity'] == 'HIGH']))" 2>/dev/null || echo "0")
        local medium_severity=$(python -c "import json; data=json.load(open('$REPORTS_DIR/bandit-report.json')); print(len([r for r in data.get('results', []) if r['issue_severity'] == 'MEDIUM']))" 2>/dev/null || echo "0")
        
        if [ "$high_severity" -gt 0 ]; then
            print_error "Bandit: $high_severity HIGH severity issues found"
            ((FAILED++))
        fi
        if [ "$medium_severity" -gt 0 ]; then
            print_warning "Bandit: $medium_severity MEDIUM severity issues found"
        fi
    fi
}

# ==================== CI ENVIRONMENT CHECKS ====================

run_env_checks() {
    print_header "CI ENVIRONMENT VERIFICATION"
    
    print_info "Checking CI environment variables..."
    
    # Check PYTHONPATH
    if [[ "$PYTHONPATH" =~ "src" ]]; then
        print_success "PYTHONPATH includes src directory"
    else
        print_error "PYTHONPATH missing src directory"
        ((FAILED++))
    fi
    
    # Check CI environment
    if [ "$CI" = "true" ]; then
        print_success "CI environment variable set"
    else
        print_error "CI environment variable not set"
        ((FAILED++))
    fi
    
    # Check required files exist
    local required_files=(
        "$PROJECT_ROOT/requirements.txt"
        "$PROJECT_ROOT/requirements/requirements-test.txt"
        "$PROJECT_ROOT/pyproject.toml"
    )
    
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "Found: $(basename $file)"
        else
            print_error "Missing: $(basename $file)"
            ((FAILED++))
        fi
    done
}

# ==================== FULL CI SIMULATION (matches ci.yml) ====================

run_full_simulation() {
    print_header "FULL CI SIMULATION (matching ci.yml workflow)"
    
    # Test Pyramid Check
    print_info "Running test pyramid check..."
    if python "$PROJECT_ROOT/scripts/testing/test-pyramid-monitor-fast.py" --format json --save-history > "$REPORTS_DIR/pyramid-report.json" 2>/dev/null; then
        SCORE=$(python -c "import json; print(json.load(open('$REPORTS_DIR/pyramid-report.json'))['score'])" 2>/dev/null || echo "0")
        print_success "Test pyramid score: $SCORE/10.0"
        
        if python -c "import json, sys; score = json.load(open('$REPORTS_DIR/pyramid-report.json'))['score']; threshold = float('$MIN_PYRAMID_SCORE'); sys.exit(0 if score >= threshold else 1)" 2>/dev/null; then
            print_success "Pyramid score meets threshold ($MIN_PYRAMID_SCORE)"
        else
            print_error "Pyramid score below threshold ($MIN_PYRAMID_SCORE)"
            ((FAILED++))
        fi
    else
        print_warning "Test pyramid check failed"
    fi
    
    # Validate markers
    print_info "Validating test markers..."
    if python "$PROJECT_ROOT/scripts/testing/validate-test-markers.py" --all 2>/dev/null; then
        print_success "Test markers validated"
    else
        print_warning "Test markers validation failed"
    fi
    
    # Run tests by marker (matches ci.yml)
    print_info "Running unit tests..."
    if pytest -m "unit" --tb=short -q 2>/dev/null; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        ((FAILED++))
    fi
    
    print_info "Running integration tests..."
    if pytest -m "integration" --tb=short -q 2>/dev/null; then
        print_success "Integration tests passed"
    else
        print_error "Integration tests failed"
        ((FAILED++))
    fi
    
    print_info "Running E2E tests..."
    if pytest -m "e2e" --tb=short -q 2>/dev/null; then
        print_success "E2E tests passed"
    else
        print_error "E2E tests failed"
        ((FAILED++))
    fi
    
    print_info "Running smoke tests..."
    if pytest -q tests/test_character_system_comprehensive.py tests/smoke/ --tb=short 2>/dev/null; then
        print_success "Smoke tests passed"
    else
        print_error "Smoke tests failed"
        ((FAILED++))
    fi
}

# ==================== HELP ====================

show_help() {
    cat << EOF
Local CI Verification Script

This script simulates the GitHub Actions CI environment locally to catch
issues before pushing. It matches the behavior of python-tests.yml and ci.yml.

Usage:
  ./scripts/ci-local.sh           # Full CI simulation (all checks)
  ./scripts/ci-local.sh --python  # Python tests only (matches python-tests.yml)
  ./scripts/ci-local.sh --quality # Quality checks only (ruff, mypy, bandit)
  ./scripts/ci-local.sh --env     # Environment verification only
  ./scripts/ci-local.sh --help    # Show this help

Environment:
  The script automatically sources .env.ci for environment variables.
  Ensure .env.ci contains:
    - PYTHONPATH
    - ORCHESTRATOR_MODE
    - CI=true

Examples:
  # Full simulation (before pushing)
  ./scripts/ci-local.sh

  # Quick Python test check
  ./scripts/ci-local.sh --python

  # Code quality only
  ./scripts/ci-local.sh --quality

  # Use with make
  make ci-local

Exit Codes:
  0 - All checks passed
  1 - One or more checks failed

For more information, see:
  - .github/workflows/python-tests.yml
  - .github/workflows/ci.yml
  - .env.ci
EOF
    exit 0
}

# ==================== MAIN ====================

main() {
    local mode="${1:---full}"
    
    # Show header
    print_header "LOCAL CI VERIFICATION"
    print_info "Simulating GitHub Actions environment..."
    print_info "Project root: $PROJECT_ROOT"
    print_info "PYTHONPATH: $PYTHONPATH"
    echo ""
    
    case "$mode" in
        --help|-h)
            show_help
            ;;
            
        --python)
            run_python_tests
            ;;
            
        --quality)
            run_quality_checks
            ;;
            
        --env)
            run_env_checks
            ;;
            
        --full|*)
            # Run everything (CI simulation)
            run_env_checks
            run_python_tests
            run_quality_checks
            run_full_simulation
            ;;
    esac
    
    # Summary
    print_header "SUMMARY"
    
    if [ $FAILED -eq 0 ]; then
        print_success "All $TOTAL_CHECKS checks passed!"
        print_info "Your code should pass GitHub Actions CI."
        echo ""
        echo -e "${GREEN}${BOLD}✅ SAFE TO COMMIT AND PUSH${NC}"
        exit 0
    else
        print_error "$FAILED of $TOTAL_CHECKS checks failed"
        print_warning "Fix issues before pushing to avoid CI failures"
        echo ""
        echo -e "${RED}${BOLD}❌ NOT SAFE TO PUSH${NC}"
        exit 1
    fi
}

# Run main
main "$@"
