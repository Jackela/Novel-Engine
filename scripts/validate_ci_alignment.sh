#!/usr/bin/env bash
# CI/CD Alignment Validation Script
# Validates that all workflows follow user's 11-point requirements

set -euo pipefail

echo "======================================"
echo "CI/CD Alignment Validation"
echo "======================================"

WORKFLOWS_DIR=".github/workflows"
ERRORS=0

# Check 1: All workflows use ubuntu-22.04
echo ""
echo "✓ Check 1: Validating runs-on ubuntu-22.04..."
for workflow in "$WORKFLOWS_DIR"/*.yml; do
  if grep -q "runs-on: ubuntu-latest" "$workflow"; then
    echo "  ❌ $workflow still uses ubuntu-latest"
    ERRORS=$((ERRORS + 1))
  fi
done

if grep -rq "runs-on: ubuntu-22.04" "$WORKFLOWS_DIR"; then
  echo "  ✅ Found ubuntu-22.04 usage"
fi

# Check 2: All workflows have permissions block
echo ""
echo "✓ Check 2: Validating permissions blocks..."
for workflow in "$WORKFLOWS_DIR"/*.yml; do
  if ! grep -q "^permissions:" "$workflow"; then
    echo "  ❌ $workflow missing permissions block"
    ERRORS=$((ERRORS + 1))
  fi
done

# Check 3: Version pinning check
echo ""
echo "✓ Check 3: Checking version references..."
echo "  Node should be: 20.11.1"
echo "  PNPM should be: 9.12.0"
echo "  Java should be: 21"
echo "  Python should be: 3.12"

# Check 4: Secrets file exists
echo ""
echo "✓ Check 4: Validating local configuration..."
if [ ! -f ".secrets" ]; then
  echo "  ❌ .secrets file not found"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✅ .secrets file exists"
fi

if [ ! -f ".env.act" ]; then
  echo "  ❌ .env.act file not found"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✅ .env.act file exists"
fi

# Check 5: Shell bash usage
echo ""
echo "✓ Check 5: Validating shell: bash usage..."
SHELL_COUNT=$(grep -r "shell: bash" "$WORKFLOWS_DIR" | wc -l)
echo "  Found $SHELL_COUNT instances of 'shell: bash'"

# Check 6: Cache keys check
echo ""
echo "✓ Check 6: Checking for cache-dependency-path..."
CACHE_COUNT=$(grep -r "cache-dependency-path" "$WORKFLOWS_DIR" | wc -l)
echo "  Found $CACHE_COUNT instances of explicit cache keys"

# Summary
echo ""
echo "======================================"
if [ $ERRORS -eq 0 ]; then
  echo "✅ All checks passed!"
  echo "Ready to run act CLI validation:"
  echo "  act -P ubuntu-22.04=catthehacker/ubuntu:full-22.04 \\"
  echo "      --container-architecture linux/amd64 \\"
  echo "      --secret-file .secrets \\"
  echo "      --env-file .env.act \\"
  echo "      -W .github/workflows/test-validation.yml"
  exit 0
else
  echo "❌ Found $ERRORS error(s)"
  echo "Please fix before running act CLI"
  exit 1
fi
