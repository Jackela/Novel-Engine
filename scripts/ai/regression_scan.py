"""Line sanitization for the AI regression diff guardrail.

Guardrail test files embed executable-looking fixture strings; before a diff
line is scanned, string contents are masked so the fixtures cannot trip the
dangerous-pattern checks meant for product code.
"""

from __future__ import annotations

import tokenize
from io import StringIO
from typing import Final

GUARDRAIL_TEST_PREFIX: Final = "tests/unit/scripts/ai/test_regression_check"
STRING_CONTENT_TOKEN_NAMES: Final = frozenset({"STRING", "FSTRING_MIDDLE"})


def guardrail_scan_line(filename: str, line: str) -> str:
    if not is_guardrail_test_file(filename):
        return line
    marker = line[:1] if line[:1] in {"+", "-"} else ""
    body = line[1:] if marker else line
    try:
        tokens = tokenize.generate_tokens(StringIO(body).readline)
        sanitized = tokenize.untokenize(
            (token.type, _scan_token_text(token)) for token in tokens
        )
    except (IndentationError, tokenize.TokenError):
        return line
    return f"{marker}{sanitized}"


def is_guardrail_test_file(filename: str) -> bool:
    return filename.startswith(GUARDRAIL_TEST_PREFIX) and filename.endswith(".py")


def _scan_token_text(token: tokenize.TokenInfo) -> str:
    token_name = tokenize.tok_name.get(token.type)
    return '""' if token_name in STRING_CONTENT_TOKEN_NAMES else token.string
