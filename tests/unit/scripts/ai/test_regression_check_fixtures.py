from __future__ import annotations

import tokenize

import pytest

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


def test_python312_fstring_content_tokens_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token_type = max(tokenize.tok_name) + 1
    monkeypatch.setitem(tokenize.tok_name, token_type, "FSTRING_MIDDLE")
    token = tokenize.TokenInfo(token_type, "except Exception:", (1, 0), (1, 17), "")

    sanitized = regression_check._scan_token_text(token)

    assert sanitized == '""'
