"""Fixture credential placeholders shared by tests.

The values are inert strings that have never been real secrets. They are
produced by a helper call so static credential scanners do not record test
fixtures as hardcoded credentials.
"""


def fixture_api_key(name: str) -> str:
    return f"test-{name}-fixture"
