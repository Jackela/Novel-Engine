from __future__ import annotations

from pathlib import Path

import pytest

from src.shared.infrastructure.config.settings import LLMSettings, NovelEngineSettings


def _write_local_env(tmp_path: Path, content: str) -> Path:
    env_file = tmp_path / ".env.local"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def _clear_dashscope_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APP_ENVIRONMENT",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_API_BASE",
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_API_BASE",
        "DASHSCOPE_MODEL",
        "DASHSCOPE_TRANSPORT_MODE",
        "DASHSCOPE_REVIEW_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_novel_engine_settings_loads_dashscope_values_from_dotenv_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_dashscope_env(monkeypatch)
    _write_local_env(
        tmp_path,
        "\n".join(
            [
                "APP_ENVIRONMENT=testing",
                "LLM_PROVIDER=dashscope",
                "LLM_MODEL=qwen3.5-flash",
                "DASHSCOPE_API_KEY=file-dashscope-key",
                "DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/api/v1",
                "DASHSCOPE_MODEL=qwen3.5-flash",
                "DASHSCOPE_TRANSPORT_MODE=multimodal_generation",
                "DASHSCOPE_REVIEW_MODEL=qwen3.5-flash",
            ]
        ),
    )

    settings = NovelEngineSettings()

    assert settings.is_testing
    assert settings.llm.provider == "dashscope"
    assert settings.llm.model == "qwen3.5-flash"
    assert settings.llm.dashscope_api_key == "file-dashscope-key"
    assert (
        settings.llm.dashscope_api_base
        == "https://dashscope.aliyuncs.com/api/v1"
    )
    assert settings.llm.dashscope_model == "qwen3.5-flash"
    assert settings.llm.dashscope_transport_mode == "multimodal_generation"
    assert settings.llm.dashscope_review_model == "qwen3.5-flash"
    assert settings.llm.resolved_model("dashscope") == "qwen3.5-flash"
    assert settings.llm.resolved_review_model("dashscope") == "qwen3.5-flash"


def test_environment_variables_override_dotenv_local_for_dashscope_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_dashscope_env(monkeypatch)
    _write_local_env(
        tmp_path,
        "\n".join(
            [
                "APP_ENVIRONMENT=testing",
                "LLM_PROVIDER=dashscope",
                "LLM_MODEL=file-model",
                "DASHSCOPE_API_KEY=file-dashscope-key",
                "DASHSCOPE_API_BASE=https://file.example.invalid/api/v1",
                "DASHSCOPE_MODEL=file-dashscope-model",
                "DASHSCOPE_REVIEW_MODEL=file-review-model",
            ]
        ),
    )

    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "env-dashscope-key")
    monkeypatch.setenv("DASHSCOPE_API_BASE", "https://env.example.invalid/api/v1")
    monkeypatch.setenv("DASHSCOPE_MODEL", "env-dashscope-model")
    monkeypatch.setenv("DASHSCOPE_REVIEW_MODEL", "env-review-model")

    settings = NovelEngineSettings()

    assert settings.llm.provider == "dashscope"
    assert settings.llm.model == "env-model"
    assert settings.llm.dashscope_api_key == "env-dashscope-key"
    assert settings.llm.dashscope_api_base == "https://env.example.invalid/api/v1"
    assert settings.llm.dashscope_model == "env-dashscope-model"
    assert settings.llm.dashscope_review_model == "env-review-model"
    assert settings.llm.resolved_model("dashscope") == "env-dashscope-model"
    assert settings.llm.resolved_review_model("dashscope") == "env-review-model"


def test_llm_settings_loads_dotenv_local_in_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_dashscope_env(monkeypatch)
    _write_local_env(
        tmp_path,
        "\n".join(
            [
                "LLM_PROVIDER=dashscope",
                "LLM_MODEL=file-model",
                "DASHSCOPE_API_KEY=isolated-file-dashscope-key",
                "DASHSCOPE_API_BASE=https://isolated.example.invalid/api/v1",
                "DASHSCOPE_MODEL=isolated-file-dashscope-model",
                "DASHSCOPE_REVIEW_MODEL=isolated-file-review-model",
            ]
        ),
    )

    settings = LLMSettings()

    assert settings.provider == "dashscope"
    assert settings.model == "file-model"
    assert settings.dashscope_api_key == "isolated-file-dashscope-key"
    assert settings.dashscope_api_base == "https://isolated.example.invalid/api/v1"
    assert settings.dashscope_model == "isolated-file-dashscope-model"
    assert settings.dashscope_review_model == "isolated-file-review-model"
    assert settings.resolved_model("dashscope") == "isolated-file-dashscope-model"
    assert settings.resolved_review_model("dashscope") == "isolated-file-review-model"


def test_resolve_dashscope_credentials_reads_dotenv_local(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _clear_dashscope_env(monkeypatch)
    _write_local_env(
        tmp_path,
        "\n".join(
            [
                "DASHSCOPE_API_KEY=helper-file-dashscope-key",
                "DASHSCOPE_API_BASE=https://helper.example.invalid/api/v1",
            ]
        ),
    )

    from tests.text_generation_contract_support import resolve_dashscope_credentials

    api_key, api_base = resolve_dashscope_credentials()

    assert api_key == "helper-file-dashscope-key"
    assert api_base == "https://helper.example.invalid/api/v1"
