"""Report generation for public API audit results."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import CheckResult, RouteKey
from .runtime import utc_now_iso


def build_report(
    *,
    discovered_routes: list[RouteKey],
    covered_routes: set[RouteKey],
    results: list[CheckResult],
) -> dict[str, Any]:
    total_checks = len(results)
    passed_checks = sum(1 for result in results if result.passed)
    failed_checks = total_checks - passed_checks

    discovered_route_set = set(discovered_routes)
    uncovered_routes = sorted(discovered_route_set - covered_routes)
    coverage = {
        "covered": len(discovered_route_set) - len(uncovered_routes),
        "total": len(discovered_route_set),
        "percent": round(
            ((len(discovered_route_set) - len(uncovered_routes)) / max(len(discovered_route_set), 1))
            * 100.0,
            2,
        ),
        "uncovered": [asdict(route) for route in uncovered_routes],
    }

    report = {
        "generated_at": utc_now_iso(),
        "summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": failed_checks,
            "overall_passed": failed_checks == 0 and not uncovered_routes,
        },
        "route_coverage": coverage,
        "routes": [asdict(route) for route in discovered_routes],
        "checks": [asdict(result) for result in results],
        "failures": [asdict(result) for result in results if not result.passed],
    }
    return report
