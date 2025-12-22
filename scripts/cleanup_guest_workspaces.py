#!/usr/bin/env python3
"""
Cleanup utility for filesystem-backed guest workspaces.

Default behavior is a dry-run. Use --yes to actually delete.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_TTL_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso8601(value: str) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iter_expired_workspaces(root: Path, ttl: timedelta) -> Iterable[Path]:
    now = _utc_now()
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        manifest = entry / "manifest.json"
        if not manifest.exists():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        ts = _parse_iso8601(data.get("lastAccessedAt") or data.get("createdAt") or "")
        if not ts:
            continue
        if now - ts > ttl:
            yield entry


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Cleanup expired guest workspaces")
    parser.add_argument(
        "--root",
        default="data/workspaces",
        help="Root directory that contains workspace folders (default: data/workspaces)",
    )
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=int(os.getenv("GUEST_WORKSPACE_TTL_DAYS", str(DEFAULT_TTL_DAYS))),
        help=f"Expire workspaces unused for N days (default: {DEFAULT_TTL_DAYS})",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete expired workspaces (default: dry-run)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if root.name != "workspaces":
        print(f"Refusing to operate on non-workspaces directory: {root}", file=sys.stderr)
        return 2

    if args.ttl_days <= 0:
        print("--ttl-days must be > 0", file=sys.stderr)
        return 2

    if not root.exists():
        print(f"No workspaces root found at: {root}")
        return 0

    ttl = timedelta(days=args.ttl_days)
    expired = list(_iter_expired_workspaces(root, ttl))

    if not expired:
        print("No expired workspaces found.")
        return 0

    print(f"Expired workspaces ({len(expired)}):")
    for path in expired:
        print(f"- {path}")

    if not args.yes:
        print("Dry-run only. Re-run with --yes to delete.")
        return 0

    deleted = 0
    for path in expired:
        try:
            shutil.rmtree(path, ignore_errors=False)
            deleted += 1
        except Exception as exc:
            print(f"Failed to delete {path}: {exc}", file=sys.stderr)

    print(f"Deleted {deleted}/{len(expired)} expired workspaces.")
    return 0 if deleted == len(expired) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

