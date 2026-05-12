"""Generate or verify the canonical OpenAPI snapshot."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _prepare_environment() -> None:
    os.environ.setdefault("APP_ENVIRONMENT", "testing")
    os.environ.setdefault(
        "SECURITY_SECRET_KEY",
        "test-secret-key-for-openapi-snapshot-1234567890",
    )
    os.environ.setdefault("MONITORING_METRICS_ENABLED", "false")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    os.environ.setdefault("LOG_STRUCTURED", "false")


def _load_openapi_schema() -> dict[str, Any]:
    _prepare_environment()
    from src.apps.api.main import create_application

    app = create_application()
    schema = app.openapi()
    if not isinstance(schema, dict):
        raise RuntimeError("OpenAPI schema generation returned a non-dict payload.")
    return schema


def _render_openapi_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write_snapshot(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _check_snapshot(output_path: Path, content: str) -> int:
    if not output_path.exists():
        print(f"[openapi-snapshot] missing snapshot: {output_path}")
        print("[openapi-snapshot] run with --write to generate it.")
        return 1

    current = output_path.read_text(encoding="utf-8")
    if current != content:
        print(f"[openapi-snapshot] drift detected: {output_path}")
        print("[openapi-snapshot] run with --write to refresh the snapshot.")
        return 1

    print(f"[openapi-snapshot] snapshot is up to date: {output_path}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="docs/api/openapi.current.json",
        help="Path to the canonical OpenAPI snapshot.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Overwrite the snapshot file with the current generated schema.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = Path(args.output).resolve()
    schema = _load_openapi_schema()
    content = _render_openapi_schema(schema)

    if args.write:
        _write_snapshot(output_path, content)
        print(f"[openapi-snapshot] wrote snapshot: {output_path}")
        return 0

    return _check_snapshot(output_path, content)


if __name__ == "__main__":
    raise SystemExit(main())
