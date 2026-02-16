#!/usr/bin/env bash
#
# ci-check.sh - Comprehensive CI validation that MUST pass before commits
#
# This script runs all CI checks locally to ensure parity with GitHub Actions.
# It is designed to be non-skippable - every check runs and results are tracked.
#
# Usage:
#   ./scripts/ci-check.sh           # Full CI (all checks)
#   ./scripts/ci-check.sh --fast    # Fast checks only (unit + pyramid + markers)
#   ./scripts/ci-check.sh --backend # Backend checks only
#   ./scripts/ci-check.sh --frontend # Frontend checks only
#   ./scripts/ci-check.sh --help    # Show help
#
# Exit codes: 0 = PASS, 1 = FAIL
# This script MUST pass before any commit is pushed.
#
# Generated report: reports/ci-report.md
#

set -o pipefail

# Configuration
MIN_PYRAMID_SCORE=5.5
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Results tracking - using associative arrays
declare -A CHECK_STATUS
declare -A CHECK_DURATION
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_SKIPPED=0

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

print_check_header() {
    echo ""
    echo -e "${BOLD}▶ $1${NC}"
    echo "─────────────────────────────────────────"
}

# Record check result
record_check() {
    local name="$1"
    local status="$2"  # pass, fail, skip
    local duration="$3"

    CHECK_STATUS["$name"]="$status"
    CHECK_DURATION["$name"]="$duration"

    case "$status" in
        pass) ((CHECKS_PASSED++)) ;;
        fail) ((CHECKS_FAILED++)) ;;
        skip) ((CHECKS_SKIPPED++)) ;;
    esac
}

# Run a check with timing
run_check() {
    local name="$1"
    local command="$2"
    local required="${3:-true}"  # true = required, false = optional

    print_check_header "$name"

    local start_time=$(date +%s)
    local exit_code=0

    # Run the command
    set +e
    eval "$command" 2>&1
    exit_code=$?
    set -e

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local duration_str="${duration}s"

    if [ "$required" = "false" ] && [ $exit_code -ne 0 ]; then
        print_warning "$name - SKIPPED (optional check failed)"
        record_check "$name" "skip" "$duration_str"
        return 0
    elif [ $exit_code -eq 0 ]; then
        print_success "$name - PASSED (${duration_str})"
        record_check "$name" "pass" "$duration_str"
        return 0
    else
        print_error "$name - FAILED (${duration_str})"
        record_check "$name" "fail" "$duration_str"
        return 1
    fi
}

# ==================== BACKEND CHECKS ====================

check_pyramid() {
    print_info "Running test pyramid analysis..."

    mkdir -p "$REPORTS_DIR"

    python "$PROJECT_ROOT/scripts/testing/test-pyramid-monitor-fast.py" \
        --format json \
        --save-history > "$REPORTS_DIR/pyramid-report.json" 2>/dev/null || true

    if [ ! -f "$REPORTS_DIR/pyramid-report.json" ]; then
        print_error "Failed to generate pyramid report"
        return 1
    fi

    # Extract score using Python
    SCORE=$(python -c "import json; print(json.load(open('$REPORTS_DIR/pyramid-report.json'))['score'])" 2>/dev/null || echo "0")

    print_info "Test Pyramid Score: $SCORE/10.0 (threshold: $MIN_PYRAMID_SCORE)"

    # Check threshold using bc
    if command -v bc &> /dev/null; then
        if (( $(echo "$SCORE < $MIN_PYRAMID_SCORE" | bc -l) )); then
            print_error "Pyramid score ($SCORE) below threshold ($MIN_PYRAMID_SCORE)"
            python "$PROJECT_ROOT/scripts/testing/test-pyramid-monitor-fast.py" --format console 2>/dev/null || true
            return 1
        fi
    else
        # Fallback without bc
        python -c "
score = float('$SCORE')
threshold = float('$MIN_PYRAMID_SCORE')
exit(0 if score >= threshold else 1)
" || {
            print_error "Pyramid score ($SCORE) below threshold ($MIN_PYRAMID_SCORE)"
            return 1
        }
    fi

    print_success "Pyramid score meets threshold"
    return 0
}

check_markers() {
    print_info "Validating test markers..."
    python "$PROJECT_ROOT/scripts/testing/validate-test-markers.py" --all --verbose
}

run_unit_tests() {
    print_info "Running unit tests..."
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    pytest -m "unit" --tb=short --durations=10 -q
}

run_integration_tests() {
    print_info "Running integration tests..."
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    pytest -m "integration" --tb=short --durations=10 -q
}

run_e2e_tests() {
    print_info "Running E2E tests..."
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    pytest -m "e2e" --tb=short --durations=10 -q
}

run_smoke_tests() {
    print_info "Running smoke tests..."
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    pytest -q tests/test_character_system_comprehensive.py tests/smoke/ --tb=short
}

# ==================== FRONTEND CHECKS ====================

run_frontend_typecheck() {
    print_info "Running frontend type check..."
    cd "$PROJECT_ROOT/frontend"
    npm run type-check
    local result=$?
    cd "$PROJECT_ROOT"
    return $result
}

run_frontend_lint() {
    print_info "Running frontend lint..."
    cd "$PROJECT_ROOT/frontend"
    npm run lint:all
    local result=$?
    cd "$PROJECT_ROOT"
    return $result
}

run_frontend_build() {
    print_info "Running frontend build..."
    cd "$PROJECT_ROOT/frontend"
    npm run build
    local result=$?
    cd "$PROJECT_ROOT"
    return $result
}

run_frontend_tests() {
    print_info "Running frontend tests..."
    cd "$PROJECT_ROOT/frontend"
    npm test -- --run
    local result=$?
    cd "$PROJECT_ROOT"
    return $result
}

run_frontend_e2e_smoke() {
    print_info "Running frontend E2E smoke tests..."
    cd "$PROJECT_ROOT/frontend"
    export PYTHONPATH="..:../src"
    npm run test:e2e:smoke
    local result=$?
    cd "$PROJECT_ROOT"
    return $result
}

# ==================== REPORT GENERATION ====================

generate_report() {
    mkdir -p "$REPORTS_DIR"

    local report_file="$REPORTS_DIR/ci-report.md"

    cat > "$report_file" << EOF
# CI Check Report

**Generated:** $TIMESTAMP
**Project:** Novel Engine

## Summary

| Metric | Count |
|--------|-------|
| ✅ Passed | $CHECKS_PASSED |
| ❌ Failed | $CHECKS_FAILED |
| ⏭️  Skipped | $CHECKS_SKIPPED |
| **Total** | $((CHECKS_PASSED + CHECKS_FAILED + CHECKS_SKIPPED)) |

## Check Results

| Check | Status | Duration |
|-------|--------|----------|
EOF

    # Add each check to the report
    for check in "${!CHECK_STATUS[@]}"; do
        local status="${CHECK_STATUS[$check]}"
        local duration="${CHECK_DURATION[$check]}"
        local status_icon

        case "$status" in
            pass) status_icon="✅ PASS" ;;
            fail) status_icon="❌ FAIL" ;;
            skip) status_icon="⏭️  SKIP" ;;
        esac

        echo "| $check | $status_icon | $duration |" >> "$report_file"
    done

    cat >> "$report_file" << EOF

## Verdict

EOF

    if [ $CHECKS_FAILED -eq 0 ]; then
        echo "**✅ ALL CHECKS PASSED** - Safe to commit and push." >> "$report_file"
    else
        echo "**❌ SOME CHECKS FAILED** - Fix issues before committing." >> "$report_file"
    fi

    echo ""
    print_info "Report saved to: $report_file"
}

# ==================== SUMMARY ====================

show_summary() {
    echo ""
    print_header "CI CHECK SUMMARY"

    echo -e "${BOLD}Results:${NC}"
    echo "  ✅ Passed:  $CHECKS_PASSED"
    echo "  ❌ Failed:  $CHECKS_FAILED"
    echo "  ⏭️  Skipped: $CHECKS_SKIPPED"
    echo ""

    # Show failed checks
    if [ $CHECKS_FAILED -gt 0 ]; then
        echo -e "${RED}${BOLD}Failed Checks:${NC}"
        for check in "${!CHECK_STATUS[@]}"; do
            if [ "${CHECK_STATUS[$check]}" = "fail" ]; then
                echo -e "  ${RED}• $check${NC}"
            fi
        done
        echo ""
    fi

    # Generate markdown report
    generate_report

    # Final verdict
    echo ""
    if [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
        echo -e "${GREEN}${BOLD}  ✅ ALL CHECKS PASSED${NC}"
        echo -e "${GREEN}${BOLD}  Safe to commit and push.${NC}"
        echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
        return 0
    else
        echo -e "${RED}${BOLD}════════════════════════════════════════${NC}"
        echo -e "${RED}${BOLD}  ❌ SOME CHECKS FAILED${NC}"
        echo -e "${RED}${BOLD}  Fix issues before committing.${NC}"
        echo -e "${RED}${BOLD}════════════════════════════════════════${NC}"
        return 1
    fi
}

# ==================== HELP ====================

show_help() {
    cat << EOF
CI Check Script - Comprehensive local CI validation

Usage:
  $0              Run all CI checks
  $0 --fast       Run fast checks only (pyramid + markers + unit tests)
  $0 --backend    Run backend checks only
  $0 --frontend   Run frontend checks only
  $0 --help       Show this help

Checks (all required unless marked optional):
  Backend:
    • Test Pyramid     - Score must be >= $MIN_PYRAMID_SCORE
    • Test Markers     - All tests must have proper markers
    • Unit Tests       - pytest -m unit
    • Integration Tests - pytest -m integration
    • E2E Tests        - pytest -m e2e
    • Smoke Tests      - Quick sanity checks

  Frontend:
    • Type Check       - npm run type-check
    • Lint             - npm run lint:all
    • Build            - npm run build
    • Tests            - npm test
    • E2E Smoke        - npm run test:e2e:smoke

Exit Codes:
  0 - All checks passed
  1 - One or more checks failed

Report:
  A detailed report is saved to reports/ci-report.md

Examples:
  $0                    # Full CI validation
  $0 --fast             # Quick validation before small changes
  $0 --backend          # Only backend checks
EOF
    exit 0
}

# ==================== MAIN ====================

main() {
    local mode="${1:---full}"

    case "$mode" in
        --help|-h)
            show_help
            ;;

        --fast)
            print_header "CI CHECK - FAST MODE"
            print_info "Running essential checks (pyramid + markers + unit tests)"

            run_check "Test Pyramid" "check_pyramid" || true
            run_check "Test Markers" "check_markers" || true
            run_check "Unit Tests" "run_unit_tests" || true

            show_summary
            exit $?
            ;;

        --backend)
            print_header "CI CHECK - BACKEND ONLY"
            print_info "Running all backend CI checks"

            run_check "Test Pyramid" "check_pyramid" || true
            run_check "Test Markers" "check_markers" || true
            run_check "Unit Tests" "run_unit_tests" || true
            run_check "Integration Tests" "run_integration_tests" || true
            run_check "E2E Tests" "run_e2e_tests" || true
            run_check "Smoke Tests" "run_smoke_tests" || true

            show_summary
            exit $?
            ;;

        --frontend)
            print_header "CI CHECK - FRONTEND ONLY"
            print_info "Running all frontend CI checks"

            # Check if frontend directory exists
            if [ ! -d "$PROJECT_ROOT/frontend" ]; then
                print_error "Frontend directory not found"
                exit 1
            fi

            run_check "Type Check" "run_frontend_typecheck" || true
            run_check "Lint" "run_frontend_lint" || true
            run_check "Build" "run_frontend_build" || true
            run_check "Tests" "run_frontend_tests" || true
            run_check "E2E Smoke" "run_frontend_e2e_smoke" || true

            show_summary
            exit $?
            ;;

        --full|*)
            print_header "CI CHECK - FULL VALIDATION"
            print_info "Running all CI checks (backend + frontend)"
            print_info "This ensures parity with GitHub Actions CI pipeline"
            echo ""

            # === BACKEND CHECKS ===
            print_header "BACKEND CHECKS"

            run_check "Test Pyramid" "check_pyramid" || true
            run_check "Test Markers" "check_markers" || true
            run_check "Unit Tests" "run_unit_tests" || true
            run_check "Integration Tests" "run_integration_tests" || true
            run_check "E2E Tests" "run_e2e_tests" || true
            run_check "Smoke Tests" "run_smoke_tests" || true

            # === FRONTEND CHECKS ===
            if [ -d "$PROJECT_ROOT/frontend" ]; then
                print_header "FRONTEND CHECKS"

                run_check "Type Check" "run_frontend_typecheck" || true
                run_check "Lint" "run_frontend_lint" || true
                run_check "Build" "run_frontend_build" || true
                run_check "Tests" "run_frontend_tests" || true
                run_check "E2E Smoke" "run_frontend_e2e_smoke" || true
            else
                print_warning "Frontend directory not found, skipping frontend checks"
            fi

            show_summary
            exit $?
            ;;
    esac
}

# Run main
main "$@"
