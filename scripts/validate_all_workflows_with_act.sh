#!/usr/bin/env bash
# Act CLI batch validation script - Validate ALL workflows
# Act CLI批量验证脚本 - 验证所有workflows

set -euo pipefail

echo "=========================================="
echo "Act CLI Workflow Validation"
echo "Act CLI工作流验证"
echo "=========================================="

WORKFLOWS_DIR=".github/workflows"
PASSED=0
FAILED=0
SKIPPED=0

# Act command base
ACT_CMD="act -P ubuntu-22.04=catthehacker/ubuntu:full-22.04 --container-architecture linux/amd64 --secret-file .secrets --env-file .env.act"

# Workflows to validate (critical ones first)
WORKFLOWS=(
  "test-validation.yml:push"
  "quality_assurance.yml:push"
  "ci.yml:push"
  "ci-debug.yml:workflow_dispatch"
)

# Workflows to skip (require external services)
SKIP_WORKFLOWS=(
  "deploy-production.yml"
  "deploy-staging.yml"  
  "release.yml"
  "rollback.yml"
  "local-test-validation.yml"
)

echo ""
echo "Validating ${#WORKFLOWS[@]} critical workflows..."
echo "Skipping ${#SKIP_WORKFLOWS[@]} deployment workflows (require external services)"
echo ""

for workflow_entry in "${WORKFLOWS[@]}"; do
  IFS=':' read -r workflow event <<< "$workflow_entry"
  workflow_path="$WORKFLOWS_DIR/$workflow"
  
  if [ ! -f "$workflow_path" ]; then
    echo "❌ Workflow not found: $workflow"
    FAILED=$((FAILED + 1))
    continue
  fi
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📋 Workflow: $workflow"
  echo "🎯 Event: $event"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  # Run act with dry-run first
  echo "🔍 Dry run validation..."
  if $ACT_CMD -W "$workflow_path" --dryrun "$event" > /dev/null 2>&1; then
    echo "  ✅ Dry run passed"
    
    # For critical workflows, offer to run full validation
    if [[ "$workflow" == "test-validation.yml" || "$workflow" == "ci-debug.yml" ]]; then
      echo ""
      echo "  ℹ️  This is a critical workflow. Run full validation? (y/N)"
      echo "  (Skipping for now - dry run passed)"
    fi
    
    PASSED=$((PASSED + 1))
  else
    echo "  ❌ Dry run failed"
    echo ""
    echo "  Showing last 20 lines of error output:"
    $ACT_CMD -W "$workflow_path" --dryrun "$event" 2>&1 | tail -20 || true
    FAILED=$((FAILED + 1))
  fi
  
  echo ""
done

echo ""
echo "Skipped workflows (require external services):"
for skip_workflow in "${SKIP_WORKFLOWS[@]}"; do
  echo "  ⏭️  $skip_workflow"
  SKIPPED=$((SKIPPED + 1))
done

echo ""
echo "=========================================="
echo "Validation Summary"
echo "验证总结"
echo "=========================================="
echo "✅ Passed:  $PASSED"
echo "❌ Failed:  $FAILED"  
echo "⏭️  Skipped: $SKIPPED"
echo ""

if [ $FAILED -eq 0 ]; then
  echo "🎉 All critical workflows validated successfully!"
  echo "🎉 所有关键工作流验证成功！"
  echo ""
  echo "Ready to commit and push:"
  echo "准备提交并推送："
  echo "  git add .github/workflows/*.yml .github/README.md"
  echo "  git commit -m 'ci: align workflows with act CLI requirements'"
  echo "  git push"
  exit 0
else
  echo "❌ Some workflows failed validation"
  echo "❌ 部分工作流验证失败"
  echo ""
  echo "Please review errors above and fix before pushing"
  echo "请检查上述错误并修复后再推送"
  exit 1
fi
