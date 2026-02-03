#!/usr/bin/env bash
# Run CodeQL security analysis locally before pushing.

set -euo pipefail

LANGUAGE=${LANGUAGE:-all}
QUICKSCAN=${QUICKSCAN:-0}
PY_BIN=${PY_BIN:-python3}
REQUIRE_CODEQL=${REQUIRE_CODEQL:-0}

echo "=== CodeQL Local Security Scan ==="
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Project: ${project_root}"

if ! command -v codeql >/dev/null 2>&1; then
  if [[ "$REQUIRE_CODEQL" == "1" ]]; then
    echo ""
    echo "CodeQL CLI is required for this scan but was not found."
    echo "Install CodeQL and re-run the scan."
    exit 1
  fi
  cat <<'EOF'

CodeQL CLI not found. Install options:
1. https://github.com/github/codeql-cli-binaries/releases
2. Using Homebrew: brew install codeql
3. Using apt (Ubuntu): sudo apt-get install codeql

EOF
  echo "Running alternative security checks with bandit..."
  if "$PY_BIN" -m bandit --version >/dev/null 2>&1; then
    echo "=== Bandit Security Scan ==="
    "$PY_BIN" -m bandit -r src/ -ll --format txt
  else
    echo "bandit not installed. Run: pip install bandit"
  fi
  exit 0
fi

db_dir="$(mktemp -d -t codeql-db-XXXXXX)"
issues_found=0

cleanup() {
  rm -rf "$db_dir"
}
trap cleanup EXIT

if [[ "$LANGUAGE" == "all" ]]; then
  languages=("python" "javascript")
else
  languages=("$LANGUAGE")
fi

for lang in "${languages[@]}"; do
  echo ""
  echo "=== Scanning ${lang} ==="
  lang_db_dir="${db_dir}/${lang}"

  if [[ "$lang" == "python" ]]; then
    codeql database create "$lang_db_dir" --language="$lang" --source-root="$project_root" --overwrite
  else
    codeql database create "$lang_db_dir" --language="$lang" --source-root="$project_root/frontend" --overwrite
  fi

  results_file="${db_dir}/${lang}-results.sarif"
  if [[ "$QUICKSCAN" == "1" ]]; then
    query_pack="codeql/${lang}-queries:codeql-suites/${lang}-security-extended.qls"
  else
    query_pack="codeql/${lang}-queries"
  fi

  codeql database analyze "$lang_db_dir" "$query_pack" --format=sarifv2.1.0 --output="$results_file"

  if [[ -f "$results_file" ]]; then
    result_count="$("$PY_BIN" - "$results_file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    data = json.load(handle)
results = data.get("runs", [{}])[0].get("results", [])
print(len(results))
PY
)"
    if [[ "$result_count" -gt 0 ]]; then
      issues_found=1
      echo "Found ${result_count} issues:"
      "$PY_BIN" - "$results_file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    data = json.load(handle)

results = data.get("runs", [{}])[0].get("results", [])
for result in results:
    rule_id = result.get("ruleId", "unknown")
    message = result.get("message", {}).get("text", "")
    location = result.get("locations", [{}])[0].get("physicalLocation", {})
    file_path = location.get("artifactLocation", {}).get("uri", "unknown")
    line = location.get("region", {}).get("startLine", 0)
    print(f"  [{rule_id}] {file_path}:{line}")
    if message:
        print(f"    {message}")
PY
    else
      echo "No security issues found."
    fi
  fi
done

if [[ "$issues_found" -ne 0 ]]; then
  exit 1
fi

echo ""
echo "=== Scan Complete ==="
