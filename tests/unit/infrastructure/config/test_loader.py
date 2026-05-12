from __future__ import annotations

from pathlib import Path

import pytest

from src.shared.infrastructure.config.loader import (
    ConfigLoader,
    ConfigLoadError,
    load_yaml_config,
    merge_configs,
)


def write_yaml(config_dir: Path, name: str, content: str) -> None:
    (config_dir / name).write_text(content, encoding="utf-8")


def test_loader_merges_base_and_environment_config(tmp_path: Path) -> None:
    write_yaml(
        tmp_path,
        "app.yaml",
        "database:\n  host: base\n  pool: 5\nfeature:\n  enabled: false\n",
    )
    write_yaml(
        tmp_path,
        "app.testing.yaml",
        "database:\n  host: testing\nfeature:\n  sample: true\n",
    )

    config = ConfigLoader(tmp_path).load("app", "testing")

    assert config == {
        "database": {"host": "testing", "pool": 5},
        "feature": {"enabled": False, "sample": True},
    }


def test_loader_uses_app_environment_when_environment_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    write_yaml(tmp_path, "app.yaml", "name: base\n")
    write_yaml(tmp_path, "app.production.yaml", "name: production\n")
    monkeypatch.setenv("APP_ENVIRONMENT", "production")

    assert ConfigLoader(tmp_path).load("app") == {"name": "production"}


def test_load_for_environment_reads_environment_file(tmp_path: Path) -> None:
    write_yaml(tmp_path, "testing.yaml", "api:\n  debug: true\n")

    assert ConfigLoader(tmp_path).load_for_environment("testing") == {
        "api": {"debug": True}
    }


def test_loader_lists_only_base_config_names(tmp_path: Path) -> None:
    write_yaml(tmp_path, "app.yaml", "name: app\n")
    write_yaml(tmp_path, "app.testing.yaml", "name: testing\n")
    write_yaml(tmp_path, "database.yaml", "name: database\n")

    loader = ConfigLoader(tmp_path)

    assert loader.list_available_configs() == ["app", "database"]
    assert loader.config_exists("app") is True
    assert loader.config_exists("missing") is False


def test_loader_treats_missing_and_empty_yaml_as_empty_config(tmp_path: Path) -> None:
    write_yaml(tmp_path, "empty.yaml", "")
    write_yaml(tmp_path, "scalar.yaml", "plain-string\n")

    loader = ConfigLoader(tmp_path)

    assert loader.load("missing", "testing") == {}
    assert loader.load("empty", "testing") == {}
    assert loader.load("scalar", "testing") == {}


def test_loader_wraps_yaml_parse_errors(tmp_path: Path) -> None:
    write_yaml(tmp_path, "broken.yaml", "root: [unclosed\n")

    with pytest.raises(ConfigLoadError, match="Failed to parse YAML file"):
        ConfigLoader(tmp_path).load("broken", "testing")


def test_loader_rejects_missing_config_directory(tmp_path: Path) -> None:
    with pytest.raises(ConfigLoadError, match="Configuration directory not found"):
        ConfigLoader(tmp_path / "missing")


def test_convenience_loader_and_merge_configs(tmp_path: Path) -> None:
    write_yaml(tmp_path, "app.yaml", "service:\n  retries: 1\n  timeout: 5\n")
    write_yaml(tmp_path, "app.testing.yaml", "service:\n  timeout: 10\n")

    config = load_yaml_config("app", "testing", tmp_path)
    merged = merge_configs(
        {"service": {"retries": 1}, "feature": False},
        {"service": {"timeout": 10}},
    )

    assert config == {"service": {"retries": 1, "timeout": 10}}
    assert merged == {"service": {"retries": 1, "timeout": 10}, "feature": False}
