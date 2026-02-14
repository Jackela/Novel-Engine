#!/usr/bin/env python3
"""
End-to-End Verification Script for Novel Engine.

This script verifies the complete flow from API to World generation,
ensuring the system produces valid output. It's designed to be run
locally for quick smoke testing.

Usage:
    python scripts/verify_e2e.py
    python scripts/verify_e2e.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class VerificationResult:
    """Result of an E2E verification test."""

    test_name: str
    passed: bool
    message: str
    data: dict[str, Any] | None = None


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_result(result: VerificationResult) -> None:
    """Print verification result with status indicator."""
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"{status} | {result.test_name}")
    print(f"       {result.message}")
    if result.data and not result.passed:
        print(f"       Data: {json.dumps(result.data, indent=2, default=str)[:500]}")


def print_world_graph(data: dict[str, Any]) -> None:
    """Pretty-print the generated World graph structure."""
    print("\n📊 Generated World Graph")
    print("-" * 40)

    # World Setting
    ws = data.get("world_setting", {})
    print(f"\n🌍 World Setting: {ws.get('name', 'Unknown')}")
    print(
        f"   Genre: {ws.get('genre')} | Era: {ws.get('era')} | Tone: {ws.get('tone')}"
    )
    print(
        f"   Magic Level: {ws.get('magic_level')}/10 | Tech Level: {ws.get('technology_level')}/10"
    )
    print(f"   Themes: {', '.join(ws.get('themes', []))}")

    # Factions
    factions = data.get("factions", [])
    print(f"\n⚔️  Factions ({len(factions)}):")
    for f in factions:
        allies = f.get("ally_count", 0)
        enemies = f.get("enemy_count", 0)
        print(f"   • {f.get('name')} [{f.get('faction_type')}]")
        print(
            f"     Alignment: {f.get('alignment')} | Influence: {f.get('influence')}/10"
        )
        print(f"     Relations: {allies} allies, {enemies} enemies")

    # Locations
    locations = data.get("locations", [])
    print(f"\n📍 Locations ({len(locations)}):")
    for loc in locations:
        controller = (
            loc.get("controlling_faction_id", "None")[:8]
            if loc.get("controlling_faction_id")
            else "Neutral"
        )
        print(f"   • {loc.get('name')} [{loc.get('location_type')}]")
        print(
            f"     Population: {loc.get('population'):,} | Danger: {loc.get('danger_level')}"
        )
        print(f"     Controller: {controller}...")

    # History Events
    events = data.get("events", [])
    print(f"\n📜 History Events ({len(events)}):")
    for evt in events:
        participants = len(evt.get("participants", []))
        print(f"   • {evt.get('name')} [{evt.get('event_type')}]")
        print(
            f"     Significance: {evt.get('significance')}/10 | Participants: {participants}"
        )

    # Summary
    print("\n📝 Generation Summary:")
    print(f"   {data.get('generation_summary', 'No summary provided')}")


def verify_health(base_url: str) -> VerificationResult:
    """Verify the API health endpoint."""
    try:
        response = requests.get(f"{base_url}/api/meta/health", timeout=10)
        if response.status_code == 200:
            return VerificationResult(
                test_name="Health Check",
                passed=True,
                message="API server is healthy and responding",
            )
        return VerificationResult(
            test_name="Health Check",
            passed=False,
            message=f"Unexpected status code: {response.status_code}",
            data={"status_code": response.status_code},
        )
    except requests.exceptions.ConnectionError:
        return VerificationResult(
            test_name="Health Check",
            passed=False,
            message=f"Cannot connect to API server at {base_url}",
        )
    except Exception as e:
        return VerificationResult(
            test_name="Health Check",
            passed=False,
            message=f"Error: {e}",
        )


def verify_world_generation(base_url: str) -> VerificationResult:
    """Verify world generation endpoint produces valid output."""
    payload = {
        "genre": "fantasy",
        "era": "medieval",
        "tone": "heroic",
        "themes": ["adventure", "magic", "conflict"],
        "magic_level": 7,
        "technology_level": 3,
        "num_factions": 3,
        "num_locations": 4,
        "num_events": 2,
    }

    try:
        response = requests.post(
            f"{base_url}/api/world/generation",
            json=payload,
            timeout=60,  # LLM calls can take a while
        )

        if response.status_code != 200:
            error_data = (
                response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else {"raw": response.text}
            )
            return VerificationResult(
                test_name="World Generation",
                passed=False,
                message=f"API returned status {response.status_code}",
                data=error_data,
            )

        data = response.json()

        # Validate structure
        required_keys = [
            "world_setting",
            "factions",
            "locations",
            "events",
            "generation_summary",
        ]
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            return VerificationResult(
                test_name="World Generation",
                passed=False,
                message=f"Missing required keys: {missing_keys}",
                data=data,
            )

        # Validate counts - allow flexibility since LLM may not generate exact counts
        actual_factions = len(data.get("factions", []))
        actual_locations = len(data.get("locations", []))
        actual_events = len(data.get("events", []))

        # Allow some flexibility (LLM may not generate exact counts)
        if actual_factions == 0 or actual_locations == 0:
            return VerificationResult(
                test_name="World Generation",
                passed=False,
                message=f"Empty results: {actual_factions} factions, {actual_locations} locations",
                data=data,
            )

        # Print the graph
        print_world_graph(data)

        return VerificationResult(
            test_name="World Generation",
            passed=True,
            message=f"Generated {actual_factions} factions, {actual_locations} locations, {actual_events} events",
            data=data,
        )

    except requests.exceptions.Timeout:
        return VerificationResult(
            test_name="World Generation",
            passed=False,
            message="Request timed out (60s) - LLM may be overloaded",
        )
    except Exception as e:
        return VerificationResult(
            test_name="World Generation",
            passed=False,
            message=f"Error: {e}",
        )


def verify_validation_error(base_url: str) -> VerificationResult:
    """Verify that validation errors are properly formatted."""
    # Send invalid payload to trigger validation error
    payload = {
        "genre": "fantasy",
        "magic_level": 999,  # Invalid: must be 0-10
        "num_factions": -5,  # Invalid: must be >= 1
    }

    try:
        response = requests.post(
            f"{base_url}/api/world/generation",
            json=payload,
            timeout=10,
        )

        if response.status_code != 422:
            return VerificationResult(
                test_name="Validation Error Format",
                passed=False,
                message=f"Expected 422, got {response.status_code}",
                data=(
                    response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else None
                ),
            )

        data = response.json()

        # Check error response structure
        if "status" not in data or data.get("status") != "error":
            return VerificationResult(
                test_name="Validation Error Format",
                passed=False,
                message="Missing or invalid 'status' field in error response",
                data=data,
            )

        if "error" not in data:
            return VerificationResult(
                test_name="Validation Error Format",
                passed=False,
                message="Missing 'error' field in error response",
                data=data,
            )

        if "errors" not in data or not isinstance(data["errors"], list):
            return VerificationResult(
                test_name="Validation Error Format",
                passed=False,
                message="Missing or invalid 'errors' array in validation response",
                data=data,
            )

        # Verify each validation error has required fields
        for err in data["errors"]:
            if "field" not in err or "message" not in err:
                return VerificationResult(
                    test_name="Validation Error Format",
                    passed=False,
                    message=f"Validation error missing required fields: {err}",
                    data=data,
                )

        return VerificationResult(
            test_name="Validation Error Format",
            passed=True,
            message=f"Error response properly formatted with {len(data['errors'])} validation errors",
            data=data,
        )

    except Exception as e:
        return VerificationResult(
            test_name="Validation Error Format",
            passed=False,
            message=f"Error: {e}",
        )


def main() -> int:
    """Run E2E verification tests."""
    parser = argparse.ArgumentParser(description="E2E Verification for Novel Engine")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API server (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print_header("Novel Engine E2E Verification")
    print(f"Target: {base_url}")

    results: list[VerificationResult] = []

    # Test 1: Health Check
    print("\n[1/3] Checking API health...")
    result = verify_health(base_url)
    results.append(result)
    print_result(result)

    if not result.passed:
        print("\n⚠️  Cannot proceed without healthy API server.")
        print("   Start the server with: python -m src.api.main_api_server")
        return 1

    # Test 2: Validation Error Format
    print("\n[2/3] Testing validation error format...")
    result = verify_validation_error(base_url)
    results.append(result)
    print_result(result)

    # Test 3: World Generation (main test)
    print("\n[3/3] Testing world generation (this may take 30-60 seconds)...")
    result = verify_world_generation(base_url)
    results.append(result)
    print_result(result)

    # Summary
    print_header("Verification Summary")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All E2E tests passed! The system is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
