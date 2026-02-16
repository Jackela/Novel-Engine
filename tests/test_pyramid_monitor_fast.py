#!/usr/bin/env python3
"""
FastTestPyramidMonitor tests.

Validates parsing of module-level tests in the pyramid monitor.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_monitor_class() -> type:
    """Load FastTestPyramidMonitor from the script path."""
    script_path = (
        Path(__file__).parent.parent
        / "scripts"
        / "testing"
        / "test-pyramid-monitor-fast.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_pyramid_monitor_fast", script_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load test-pyramid-monitor-fast.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FastTestPyramidMonitor


def test_module_level_tests_are_detected(tmp_path: Path) -> None:
    """Ensure module-level tests are included in parsed results."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_sample.py"
    test_file.write_text(
        "import pytest\n\n"
        "pytestmark = pytest.mark.unit\n\n"
        "def test_module_level():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    monitor = _load_monitor_class()(project_root=tmp_path)
    monitor._parse_test_file(test_file)

    expected_id = "tests/test_sample.py::test_module_level"
    assert expected_id in monitor.all_tests
    assert expected_id in monitor.tests_by_marker["unit"]
