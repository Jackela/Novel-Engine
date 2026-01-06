#!/usr/bin/env python3
"""
Cache Savings Report
====================

Generates a simple report of estimated token and cost savings
from the global cache/coordinator metrics publisher.

Usage:
  python scripts/reporting/cache_savings_report.py --format csv|md --output -
"""

import argparse
import sys
from datetime import datetime, timezone

try:
    from src.metrics.global_metrics import metrics as global_metrics
except Exception as e:
    print(f"ERROR: unable to import metrics: {e}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["csv", "md"], default="md")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    snap = global_metrics.snapshot().to_dict()
    rows = [
        [
            snap.get("ts", datetime.now(timezone.utc).isoformat()),
            snap.get("saved_tokens", 0),
            snap.get("saved_cost", 0.0),
            snap.get("cache_exact_hits", 0),
            snap.get("cache_semantic_hits", 0),
        ]
    ]

    out = sys.stdout if args.output == "-" else open(args.output, "w", encoding="utf-8")
    try:
        if args.format == "csv":
            print(
                "timestamp,saved_tokens,saved_cost,exact_hits,semantic_hits", file=out
            )
            for r in rows:
                print(
                    f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]}",
                    file=out,
                )
        else:  # md
            print("# Cache Savings Report\n", file=out)
            print(
                "| Timestamp | Saved Tokens | Saved Cost | Exact Hits | Semantic Hits |",
                file=out,
            )
            print(
                "|-----------|--------------|------------|------------|---------------|",
                file=out,
            )
            for r in rows:
                print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |", file=out)
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
