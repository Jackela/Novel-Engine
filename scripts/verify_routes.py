#!/usr/bin/env python3
"""
Route verification script for Novel Engine frontend.

Verifies that all expected routes return 200 OK (HTML content),
not 404 errors. This ensures React Router is correctly configured.

Usage:
    python scripts/verify_routes.py [--base-url URL]

Example:
    python scripts/verify_routes.py --base-url http://localhost:3000
"""

import argparse
import sys
from typing import NamedTuple

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)


class RouteCheck(NamedTuple):
    """Result of a route verification check."""

    path: str
    status_code: int
    is_html: bool
    error: str | None


# Routes that should return HTML (React app)
EXPECTED_ROUTES = [
    "/",
    "/login",
    "/weaver",
    "/dashboard",
    "/world",
    "/story",
    "/stories",
    "/characters",
    "/campaigns",
]


def check_route(client: httpx.Client, base_url: str, path: str) -> RouteCheck:
    """
    Check if a route returns valid HTML.

    Args:
        client: HTTP client instance
        base_url: Base URL of the frontend server
        path: Route path to check

    Returns:
        RouteCheck with status code and HTML validation result
    """
    url = f"{base_url.rstrip('/')}{path}"
    try:
        response = client.get(url, follow_redirects=True, timeout=10.0)
        content_type = response.headers.get("content-type", "")
        is_html = "text/html" in content_type
        return RouteCheck(
            path=path, status_code=response.status_code, is_html=is_html, error=None
        )
    except httpx.RequestError as e:
        return RouteCheck(path=path, status_code=0, is_html=False, error=str(e))


def main() -> int:
    """
    Main entry point for route verification.

    Returns:
        Exit code (0 for success, 1 for failures)
    """
    parser = argparse.ArgumentParser(description="Verify frontend routes")
    parser.add_argument(
        "--base-url",
        default="http://localhost:3000",
        help="Base URL of the frontend server (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    args = parser.parse_args()

    print(f"Verifying routes at {args.base_url}")
    print("-" * 50)

    passed = 0
    failed = 0
    results: list[RouteCheck] = []

    with httpx.Client() as client:
        for path in EXPECTED_ROUTES:
            result = check_route(client, args.base_url, path)
            results.append(result)

            if result.error:
                status = "ERROR"
                failed += 1
            elif result.status_code == 200 and result.is_html:
                status = "OK"
                passed += 1
            else:
                status = "FAIL"
                failed += 1

            # Print result
            if args.verbose or status != "OK":
                detail = ""
                if result.error:
                    detail = f" ({result.error})"
                elif not result.is_html:
                    detail = " (not HTML)"
                print(f"  [{status}] {path} -> {result.status_code}{detail}")
            else:
                print(f"  [OK] {path}")

    print("-" * 50)
    print(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("\nFailed routes need attention:")
        for result in results:
            if result.error or result.status_code != 200 or not result.is_html:
                print(f"  - {result.path}")
        return 1

    print("\nAll routes verified successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
