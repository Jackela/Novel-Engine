from __future__ import annotations

import pytest

from scripts.ai import regression_check


def test_build_diff_command_uses_local_diff_when_refs_are_absent() -> None:
    # Given
    base_ref = None
    head_ref = None

    # When
    command = regression_check.build_diff_command(base_ref, head_ref)

    # Then
    assert command == ["git", "diff", "--no-color"]


def test_build_diff_command_uses_base_and_head_refs_together() -> None:
    # Given
    base_ref = "origin/main"
    head_ref = "HEAD"

    # When
    command = regression_check.build_diff_command(base_ref, head_ref)

    # Then
    assert command == ["git", "diff", "--no-color", "origin/main...HEAD"]


def test_build_diff_command_rejects_partial_ref_configuration() -> None:
    # Given / When / Then
    with pytest.raises(ValueError, match="provided together"):
        regression_check.build_diff_command("origin/main", None)


def test_parse_diff_groups_additions_deletions_and_deleted_files() -> None:
    # Given
    diff_text = "\n".join(
        [
            "diff --git a/src/app.py b/src/app.py",
            "--- a/src/app.py",
            "+++ b/src/app.py",
            "@@ -1 +1 @@",
            "-validate(user)",
            "+authorize(user)",
            "diff --git a/tests/test_app.py b/tests/test_app.py",
            "deleted file mode 100644",
            "--- a/tests/test_app.py",
            "+++ /dev/null",
        ]
    )

    # When
    details = regression_check.parse_diff(diff_text)

    # Then
    assert details.additions == {"src/app.py": ["+authorize(user)"]}
    assert details.deletions == {"src/app.py": ["-validate(user)"]}
    assert details.deleted_files == {"tests/test_app.py"}


def test_parse_diff_keeps_deleted_file_hunk_lines_for_safety_checks() -> None:
    # Given
    diff_text = "\n".join(
        [
            "diff --git a/src/auth.py b/src/auth.py",
            "deleted file mode 100644",
            "--- a/src/auth.py",
            "+++ /dev/null",
            "@@ -1 +0,0 @@",
            "-raise PermissionError()",
        ]
    )

    # When
    details = regression_check.parse_diff(diff_text)
    issues = regression_check.check_deleted_safety_lines(details)

    # Then
    assert details.deleted_files == {"src/auth.py"}
    assert details.deletions == {"src/auth.py": ["-raise PermissionError()"]}
    assert issues == [
        "[src/auth.py] Deleted safety keyword 'raise': -raise PermissionError()"
    ]


def test_dangerous_additions_report_ai_risk_patterns() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={
            "src/app.py": [
                "+except Exception:",
                '+query = f"SELECT * FROM documents WHERE id={document_id}"',
                '+password = "not-a-real-secret"',
            ],
            "frontend/src/app.ts": [
                "+const value = payload as any;",
                "+element.innerHTML = markdown;",
            ],
        },
        deletions={},
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_dangerous_additions(details)

    # Then
    assert issues == [
        "[src/app.py] broad except: +except Exception:",
        '[src/app.py] SQL/FTS5 f-string: +query = f"SELECT * FROM documents WHERE id={document_id}"',
        '[src/app.py] hardcoded secret-like value: +password = "not-a-real-secret"',
        "[frontend/src/app.ts] TypeScript any escape: +const value = payload as any;",
        "[frontend/src/app.ts] unsafe DOM/code execution: +element.innerHTML = markdown;",
    ]


def test_deleted_safety_lines_are_reported_in_tests_and_source() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={},
        deletions={
            "src/auth.py": ["-raise PermissionError()"],
            "tests/test_auth.py": ["-assert validate(user)"],
        },
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_deleted_safety_lines(details)

    # Then
    assert issues == [
        "[src/auth.py] Deleted safety keyword 'raise': -raise PermissionError()",
        "[tests/test_auth.py] Deleted safety keyword 'validate': -assert validate(user)",
    ]


def test_moved_safety_lines_are_not_reported_as_deleted() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={
            "tests/fakes/fake_studio_repository_jobs.py": [
                '+            raise NotFound("Job not found.")',
            ],
        },
        deletions={
            "tests/fakes/fake_studio_repository.py": [
                '-            raise NotFound("Job not found.")',
            ],
        },
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_deleted_safety_lines(details)

    # Then
    assert issues == []


def test_session_secret_constructor_upgrade_is_not_reported_as_deleted_auth() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={
            "src/contexts/studio/application/services/facade_base.py": [
                "+        self.auth = AuthService(repository, self.session_secret)"
            ]
        },
        deletions={
            "src/contexts/studio/application/services/facade_base.py": [
                "-        self.auth = AuthService(repository)"
            ]
        },
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_deleted_safety_lines(details)

    # Then
    assert issues == []


def test_deleted_safety_keyword_comments_are_not_reported() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={},
        deletions={"tests/fakes/fake_studio_repository.py": ["-    # Health and auth"]},
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_deleted_safety_lines(details)

    # Then
    assert issues == []


def test_deleted_test_files_and_forbidden_paths_are_reported() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={},
        deletions={},
        deleted_files={"tests/test_auth.py", "data/prod.sqlite3"},
    )

    # When
    issues = regression_check.check_deleted_files(details)

    # Then
    assert issues == [
        "[data/prod.sqlite3] Deleted forbidden-zone file",
        "[tests/test_auth.py] Deleted test file",
    ]


def test_guardrail_self_modification_reports_short_circuit() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={"scripts/ai/regression_check.py": ["+    return []"]},
        deletions={},
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_guardrail_self_modification(details)

    # Then
    assert issues == [
        "[scripts/ai/regression_check.py] guardrail short-circuit: +    return []"
    ]


def test_file_scope_reports_count_and_forbidden_prefixes() -> None:
    # Given
    details = regression_check.DiffDetails(
        additions={f"src/file_{index}.py": ["+value = 1"] for index in range(6)}
        | {"alembic/versions/0004.py": ["+value = 1"]},
        deletions={},
        deleted_files=set(),
    )

    # When
    issues = regression_check.check_file_scope(
        details,
        max_files=5,
        skip_file_count=False,
    )

    # Then
    assert issues == [
        "AI changed 7 files. Consider splitting into smaller tasks.",
        "AI modified forbidden zone: alembic/versions/0004.py",
    ]


def test_main_can_skip_file_count_for_ci_scope_policy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    diff_text = "\n".join(
        [
            f"diff --git a/src/file_{index}.py b/src/file_{index}.py\n"
            f"--- a/src/file_{index}.py\n"
            f"+++ b/src/file_{index}.py\n"
            "+value = 1"
            for index in range(6)
        ]
    )

    def fake_run_git_diff(
        base_ref: str | None = None,
        head_ref: str | None = None,
    ) -> str:
        assert base_ref is None
        assert head_ref is None
        return diff_text

    monkeypatch.setattr(regression_check, "run_git_diff", fake_run_git_diff)

    # When
    result = regression_check.main(["--skip-file-count"])

    # Then
    captured = capsys.readouterr()
    assert result == 0
    assert (
        captured.out
        == "[PASS] Regression check passed. No obvious AI anti-patterns detected.\n"
    )
    assert captured.err == ""
