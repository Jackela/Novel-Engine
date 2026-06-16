from __future__ import annotations

import pytest

from src.apps.cli.novel_engine import main


def test_help_does_not_require_production_secrets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.delenv("SECURITY_SECRET_KEY", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    assert "novel-engine" in capsys.readouterr().out
