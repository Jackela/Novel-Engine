#!/bin/bash
# ACT Environment Verification Script
# Verifies local ACT environment matches GitHub Actions CI environment

set -euo pipefail

echo "════════════════════════════════════════════════════════"
echo "  ACT Environment Verification for Novel-Engine"
echo "════════════════════════════════════════════════════════"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓${NC} $1"; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# Check function
check() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    
    if [ "$expected" = "$actual" ]; then
        success "$name: $actual"
        return 0
    else
        warning "$name: Expected '$expected', got '$actual'"
        return 1
    fi
}

# ============================================
# System Information
# ============================================

echo "📋 System Information"
echo "────────────────────────────────────────────────────────"

echo "Platform: $(uname -s)"
echo "Architecture: $(uname -m)"
echo "Kernel: $(uname -r)"
echo "Available CPUs: $(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 'unknown')"

if command -v free >/dev/null 2>&1; then
    echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
fi

echo ""

# ============================================
# Python Environment
# ============================================

echo "🐍 Python Environment"
echo "────────────────────────────────────────────────────────"

if command -v python >/dev/null 2>&1; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    check "Python Version" "3.11.x" "${PYTHON_VERSION}"
else
    error "Python not found in PATH"
    exit 1
fi

if command -v pip >/dev/null 2>&1; then
    PIP_VERSION=$(pip --version | awk '{print $2}')
    success "pip Version: $PIP_VERSION"
else
    error "pip not found in PATH"
    exit 1
fi

echo ""

# ============================================
# Python Packages
# ============================================

echo "📦 Python Packages"
echo "────────────────────────────────────────────────────────"

required_packages=("pytest" "pyyaml" "anthropic")

for package in "${required_packages[@]}"; do
    if pip show "$package" >/dev/null 2>&1; then
        version=$(pip show "$package" | grep "Version:" | awk '{print $2}')
        success "$package: $version"
    else
        error "$package not installed"
    fi
done

echo ""

# ============================================
# Test Framework
# ============================================

echo "🧪 Test Framework"
echo "────────────────────────────────────────────────────────"

if command -v pytest >/dev/null 2>&1; then
    PYTEST_VERSION=$(pytest --version 2>&1 | head -1)
    success "$PYTEST_VERSION"
else
    error "pytest not found in PATH"
fi

echo ""

# ============================================
# GitHub Actions Environment Variables
# ============================================

echo "🔧 GitHub Actions Environment"
echo "────────────────────────────────────────────────────────"

check "CI" "true" "${CI:-false}"
check "GITHUB_ACTIONS" "true" "${GITHUB_ACTIONS:-false}"
check "RUNNER_OS" "Linux" "${RUNNER_OS:-unknown}"
check "RUNNER_ARCH" "X64" "${RUNNER_ARCH:-unknown}"
check "PYTHON_VERSION" "3.11" "${PYTHON_VERSION:-unknown}"

echo ""

# ============================================
# File Structure
# ============================================

echo "📁 Required Files"
echo "────────────────────────────────────────────────────────"

required_files=(
    ".actrc"
    ".act-event.json"
    ".env.example"
    "requirements.txt"
    "requirements-test.txt"
    ".github/workflows/ci.yml"
    "tests/test_enhanced_bridge.py"
    "tests/test_character_system_comprehensive.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        success "$file exists"
    else
        error "$file missing"
    fi
done

echo ""

# ============================================
# Test Execution
# ============================================

echo "🏃 Test Execution"
echo "────────────────────────────────────────────────────────"

if [ -f "tests/test_enhanced_bridge.py" ]; then
    echo "Running test_enhanced_bridge.py..."
    if pytest tests/test_enhanced_bridge.py -q --tb=no >/dev/null 2>&1; then
        success "test_enhanced_bridge.py passed"
    else
        warning "test_enhanced_bridge.py failed (check pytest output)"
    fi
fi

if [ -f "tests/test_character_system_comprehensive.py" ]; then
    echo "Running test_character_system_comprehensive.py..."
    if pytest tests/test_character_system_comprehensive.py -q --tb=no >/dev/null 2>&1; then
        success "test_character_system_comprehensive.py passed"
    else
        warning "test_character_system_comprehensive.py failed (check pytest output)"
    fi
fi

echo ""

# ============================================
# ACT Configuration
# ============================================

echo "🎬 ACT Configuration"
echo "────────────────────────────────────────────────────────"

if [ -f ".env.local" ]; then
    if grep -q "GITHUB_TOKEN=ghp_" .env.local 2>/dev/null; then
        success ".env.local configured with GitHub token"
    else
        warning ".env.local exists but GITHUB_TOKEN may not be set"
    fi
else
    warning ".env.local not found (create from .env.local.template)"
fi

if [ -f ".env" ]; then
    success ".env file exists"
else
    warning ".env not found (copy from .env.example)"
fi

echo ""

# ============================================
# Summary
# ============════════════════════════════════

echo "════════════════════════════════════════════════════════"
echo "  Verification Complete"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. If .env.local is missing, create it: cp .env.local.template .env.local"
echo "2. Add GitHub PAT to .env.local: GITHUB_TOKEN=ghp_your_token"
echo "3. Test ACT: act -W .github/workflows/ci.yml -j tests --dryrun"
echo "4. Run full CI: act -W .github/workflows/ci.yml -j tests"
echo ""
echo "See .claude/ACT_SETUP.md for detailed configuration guide"
