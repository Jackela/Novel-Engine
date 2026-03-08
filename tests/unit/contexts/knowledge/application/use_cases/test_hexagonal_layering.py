"""Hexagonal layering guardrails for knowledge application use cases.

These tests prevent regressions where application use cases import infrastructure
modules directly, which violates the dependency direction.
"""

from pathlib import Path
import re

import pytest


pytestmark = pytest.mark.unit

pytestmark = [pytest.mark.unit, pytest.mark.fast]


USE_CASE_FILES = [
    Path("src/contexts/knowledge/application/use_cases/retrieve_agent_context.py"),
    Path("src/contexts/knowledge/application/use_cases/create_knowledge_entry.py"),
    Path("src/contexts/knowledge/application/use_cases/update_knowledge_entry.py"),
    Path("src/contexts/knowledge/application/use_cases/delete_knowledge_entry.py"),
]


@pytest.mark.parametrize("file_path", USE_CASE_FILES)
def test_use_case_does_not_import_infrastructure(file_path: Path) -> None:
    """Why: keep application-layer dependencies pointed inward to ports/domain only."""
    source = file_path.read_text(encoding="utf-8")
    assert not re.search(
        r"^\s*(from|import)\s+.*infrastructure",
        source,
        flags=re.MULTILINE,
    )
