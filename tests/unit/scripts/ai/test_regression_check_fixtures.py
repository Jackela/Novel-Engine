from __future__ import annotations

from scripts.ai import regression_check

_GUARDRAIL_TEST_FILE = "tests/unit/scripts/ai/test_regression_check_fixtures.py"


def test_guardrail_fixture_strings_are_not_dangerous_additions() -> None:
    details = regression_check.DiffDetails(
        additions={
            _GUARDRAIL_TEST_FILE: [
                '+                "+except Exception:",',
                '+        "[src/app.py] broad except: +except Exception:",',
            ]
        },
        deletions={},
        deleted_files=set(),
    )

    issues = regression_check.check_dangerous_additions(details)

    assert issues == []


def test_guardrail_fixture_strings_are_not_deleted_safety_issues() -> None:
    details = regression_check.DiffDetails(
        additions={},
        deletions={_GUARDRAIL_TEST_FILE: ['-        "+raise PermissionError()",']},
        deleted_files=set(),
    )

    issues = regression_check.check_deleted_safety_lines(details)

    assert issues == []


def test_guardrail_test_executable_dangerous_lines_are_still_reported() -> None:
    details = regression_check.DiffDetails(
        additions={_GUARDRAIL_TEST_FILE: ["+except Exception:"]},
        deletions={},
        deleted_files=set(),
    )

    issues = regression_check.check_dangerous_additions(details)

    assert issues == [f"[{_GUARDRAIL_TEST_FILE}] broad except: +except Exception:"]
