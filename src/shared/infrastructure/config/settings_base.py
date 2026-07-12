from __future__ import annotations

from typing import Any, cast

from pydantic_settings import SettingsConfigDict

__all__ = ["LOCAL_DOTENV_FILE", "_settings_config"]

LOCAL_DOTENV_FILE = ".env.local"


def _settings_config(
    *,
    env_prefix: str,
    env_nested_delimiter: str | None = None,
    validate_default: bool | None = None,
    populate_by_name: bool | None = None,
) -> SettingsConfigDict:
    config: dict[str, Any] = {
        "env_file": LOCAL_DOTENV_FILE,
        "env_file_encoding": "utf-8",
        "env_prefix": env_prefix,
        "extra": "ignore",
        "case_sensitive": False,
    }
    if env_nested_delimiter is not None:
        config["env_nested_delimiter"] = env_nested_delimiter
    if validate_default is not None:
        config["validate_default"] = validate_default
    if populate_by_name is not None:
        config["populate_by_name"] = populate_by_name
    return cast(SettingsConfigDict, config)
