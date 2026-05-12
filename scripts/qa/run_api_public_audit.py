"""Run a structured audit over all public FastAPI routes.

The audit is designed for local and CI use:
- runs deterministic checks against the canonical in-process app
- validates route behavior (positive + key negative semantics)
- reports method+path coverage of discovered public routes
- writes a structured JSON evidence file
- exits non-zero on any failing check or uncovered route
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.qa.api_public_audit.checks import execute_checks
from scripts.qa.api_public_audit.executor import AuditRunner
from scripts.qa.api_public_audit.reporting import build_report
from scripts.qa.api_public_audit.runtime import (
    build_canonical_client,
    discover_public_routes,
    reset_runtime_singletons,
)


def run_audit(output_path: Path) -> int:
    client, app = build_canonical_client()
    discovered_routes = discover_public_routes(app)
    runner = AuditRunner(client=client, discovered_routes=discovered_routes)

    execute_checks(runner)
    report = build_report(
        discovered_routes=discovered_routes,
        covered_routes=runner.covered_routes,
        results=runner.results,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = report["summary"]
    coverage = report["route_coverage"]
    uncovered = [route for route in coverage["uncovered"]]

    print(
        "[api-public-audit] checks:"
        f" {summary['passed']}/{summary['total_checks']} passed, {summary['failed']} failed"
    )
    print(
        "[api-public-audit] coverage:"
        f" {coverage['covered']}/{coverage['total']} routes ({coverage['percent']}%)"
    )
    print(f"[api-public-audit] report: {output_path}")

    if summary["failed"] > 0 or uncovered:
        if uncovered:
            uncovered_summary = ", ".join(
                f"{route['method']} {route['path']}" for route in uncovered
            )
            print(f"[api-public-audit] uncovered routes: {uncovered_summary}")
        client.close()
        return 1

    client.close()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="artifacts/qa/api-public-audit.json",
        help="Path to the JSON report file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    exit_code = 1
    try:
        exit_code = run_audit(output_path.resolve())
    finally:
        try:
            reset_runtime_singletons()
        except Exception:
            # Best-effort cleanup only.
            pass
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
