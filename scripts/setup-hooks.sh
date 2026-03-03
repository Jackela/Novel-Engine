#!/usr/bin/env bash
#
# setup-hooks.sh - Configure git hooks for CI validation
#
# This script configures git to use the .githooks directory
# for pre-push CI validation.

set -e

HOOKS_DIR=".githooks"

echo ""
echo "🔧 Setting up git hooks..."
echo ""

# Check if .githooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ Error: .githooks directory not found"
    echo "   Make sure you're running this from the project root"
    exit 1
fi

# Configure git to use .githooks directory
git config core.hooksPath .githooks

if [ $? -eq 0 ]; then
    echo "✅ Git hooks configured successfully!"
    echo ""
    echo "   Hooks installed:"
    ls -la "$HOOKS_DIR" | grep -v "^total" | while read -r line; do
        hook=$(echo "$line" | awk '{print $NF}')
        if [ -n "$hook" ]; then
            echo "   - $hook"
        fi
    done
    echo ""
    echo "   The pre-push hook will run CI checks before every push."
    echo "   To bypass (emergency only): git push --no-verify"
    echo ""
else
    echo "❌ Failed to configure git hooks"
    exit 1
fi
