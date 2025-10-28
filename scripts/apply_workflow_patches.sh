#!/usr/bin/env bash
# Batch workflow patching script - Apply CI/CD alignment to all workflows
# 批量工作流补丁脚本 - 对所有workflows应用CI/CD对齐

set -euo pipefail

echo "=========================================="
echo "Applying CI/CD Alignment Patches"
echo "应用CI/CD对齐补丁"
echo "=========================================="

WORKFLOWS_DIR=".github/workflows"
BACKUP_DIR=".github/workflows.backup.$(date +%Y%m%d_%H%M%S)"

# Create backup
echo ""
echo "📦 Creating backup..."
cp -r "$WORKFLOWS_DIR" "$BACKUP_DIR"
echo "✅ Backup created: $BACKUP_DIR"

# Define patch function
apply_patch() {
  local file=$1
  local description=$2
  
  echo ""
  echo "🔧 Patching: $file"
  echo "   $description"
  
  # Patch 1: ubuntu-latest -> ubuntu-22.04
  if grep -q "runs-on: ubuntu-latest" "$file"; then
    sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-22.04/g' "$file"
    echo "   ✅ Updated runs-on to ubuntu-22.04"
  fi
  
  # Patch 2: Add permissions if missing
  if ! grep -q "^permissions:" "$file"; then
    # Insert permissions after 'on:' block
    awk '/^on:/ {
      print; 
      while (getline && /^  /) print;
      print "";
      print "permissions:";
      print "  contents: read";
      print "";
      next;
    } {print}' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    echo "   ✅ Added permissions block"
  fi
  
  # Patch 3: Add shell: bash to run blocks (if not already present)
  if grep -q "run: |" "$file" && ! grep -B1 "run: |" "$file" | grep -q "shell: bash"; then
    # This requires more sophisticated processing - we'll mark it for manual review
    echo "   ⚠️  May need 'shell: bash' - please verify"
  fi
  
  # Patch 4: Update Python version references to 3.12
  if grep -q "PYTHON_VERSION: '3\\.1[01]'" "$file"; then
    sed -i "s/PYTHON_VERSION: '3\\.1[01]'/PYTHON_VERSION: '3.12'/g" "$file"
    echo "   ✅ Updated Python version to 3.12"
  fi
  
  # Patch 5: Add cache-dependency-path to setup-python if missing
  if grep -q "uses: actions/setup-python" "$file"; then
    if grep -A5 "uses: actions/setup-python" "$file" | grep -q "cache: 'pip'" | head -1; then
      if ! grep -A5 "uses: actions/setup-python" "$file" | grep -q "cache-dependency-path" | head -1; then
        # Add cache-dependency-path after cache: 'pip'
        sed -i "/cache: 'pip'/a\\        cache-dependency-path: requirements.txt" "$file"
        echo "   ✅ Added cache-dependency-path"
      fi
    fi
  fi
  
  echo "   ✅ Patching complete"
}

# Apply patches to remaining 6 workflows
echo ""
echo "Applying patches to 6 workflows..."

apply_patch "$WORKFLOWS_DIR/ci.yml" "Main CI pipeline"
apply_patch "$WORKFLOWS_DIR/deploy-production.yml" "Production deployment"
apply_patch "$WORKFLOWS_DIR/deploy-staging.yml" "Staging deployment"
apply_patch "$WORKFLOWS_DIR/local-test-validation.yml" "Local test validation"
apply_patch "$WORKFLOWS_DIR/release.yml" "Release workflow"
apply_patch "$WORKFLOWS_DIR/rollback.yml" "Rollback workflow"

echo ""
echo "=========================================="
echo "✅ All patches applied successfully!"
echo "✅ 所有补丁应用成功！"
echo ""
echo "Backup location: $BACKUP_DIR"
echo "备份位置: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Review changes: git diff $WORKFLOWS_DIR"
echo "2. Validate with act CLI for each workflow"
echo "3. Commit when all pass"
echo ""
echo "下一步："
echo "1. 检查更改: git diff $WORKFLOWS_DIR"
echo "2. 用act CLI验证每个workflow"
echo "3. 全部通过后提交"
echo "=========================================="
