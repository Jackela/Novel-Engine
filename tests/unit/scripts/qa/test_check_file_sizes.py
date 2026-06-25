from __future__ import annotations

from pathlib import Path

import pytest

from scripts.qa import check_file_sizes


def _write_code_lines(path: Path, line_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("value = 1\n" * line_count, encoding="utf-8")


def test_exact_active_legacy_ceiling_is_accepted() -> None:
    # Given
    relative_path = "src/contexts/studio/application/ports/studio_repository.py"
    path = check_file_sizes.ROOT / relative_path
    configured_limit = check_file_sizes.LEGACY_LIMITS[relative_path]
    assert configured_limit > check_file_sizes.MAX_CODE_LINES
    assert check_file_sizes.code_line_count(path) == configured_limit

    # When
    violations = check_file_sizes.file_size_violations([path])

    # Then
    assert violations == []


def test_legacy_limit_violations_reports_missing_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    relative_path = "src/missing.py"
    monkeypatch.setattr(check_file_sizes, "ROOT", tmp_path)
    monkeypatch.setattr(check_file_sizes, "LEGACY_LIMITS", {relative_path: 301})

    # When
    violations = check_file_sizes.legacy_limit_violations()

    # Then
    assert violations == [f"{relative_path}: legacy baseline file is missing"]


@pytest.mark.parametrize(
    "line_count",
    [check_file_sizes.MAX_CODE_LINES - 1, check_file_sizes.MAX_CODE_LINES],
)
def test_legacy_limit_violations_reports_file_at_or_below_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line_count: int
) -> None:
    # Given
    relative_path = "src/stale.py"
    path = tmp_path / relative_path
    _write_code_lines(path, line_count)
    monkeypatch.setattr(check_file_sizes, "ROOT", tmp_path)
    monkeypatch.setattr(
        check_file_sizes,
        "LEGACY_LIMITS",
        {relative_path: check_file_sizes.MAX_CODE_LINES + 1},
    )

    # When
    violations = check_file_sizes.legacy_limit_violations()

    # Then
    assert violations == [
        f"{relative_path}: stale legacy baseline; {line_count} code lines is at or "
        f"below default limit {check_file_sizes.MAX_CODE_LINES}"
    ]


def test_legacy_limit_violations_reports_mismatched_over_default_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    relative_path = "src/inexact.py"
    current_count = check_file_sizes.MAX_CODE_LINES + 1
    configured_limit = current_count + 1
    path = tmp_path / relative_path
    _write_code_lines(path, current_count)
    monkeypatch.setattr(check_file_sizes, "ROOT", tmp_path)
    monkeypatch.setattr(
        check_file_sizes,
        "LEGACY_LIMITS",
        {relative_path: configured_limit},
    )

    # When
    violations = check_file_sizes.legacy_limit_violations()

    # Then
    assert violations == [
        f"{relative_path}: stale legacy baseline; configured limit {configured_limit} "
        f"differs from current count {current_count}"
    ]


def test_main_reports_invalid_legacy_baselines_before_file_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    relative_path = "src/missing.py"
    monkeypatch.setattr(check_file_sizes, "ROOT", tmp_path)
    monkeypatch.setattr(check_file_sizes, "LEGACY_LIMITS", {relative_path: 301})

    def fail_if_scanned() -> list[Path]:
        raise AssertionError("ordinary file-size scanning must not run")

    monkeypatch.setattr(check_file_sizes, "tracked_and_new_files", fail_if_scanned)

    # When
    result = check_file_sizes.main()

    # Then
    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == (
        "[file-size] invalid legacy baselines:\n"
        f"  {relative_path}: legacy baseline file is missing\n"
    )
