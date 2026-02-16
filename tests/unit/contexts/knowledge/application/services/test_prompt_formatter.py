"""
Unit tests for PromptFormatter service.

Tests prompt format selection and rendering for different model families.
"""

import pytest

from src.contexts.knowledge.application.services.prompt_formatter import (
    FormattedPrompt,
    PromptFormat,
    PromptFormatter,
    PromptModelFamily,
    PromptRequest,
    create_prompt_formatter,
)

pytestmark = pytest.mark.unit


class TestPromptRequest:
    """Tests for PromptRequest dataclass."""

    def test_create_minimal_request(self) -> None:
        """Test creating a minimal prompt request."""
        request = PromptRequest(user_prompt="Hello, world!")
        assert request.user_prompt == "Hello, world!"
        assert request.system_prompt is None
        assert request.conversation_history is None

    def test_create_full_request(self) -> None:
        """Test creating a full prompt request."""
        request = PromptRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello!",
            conversation_history=[("user", "Hi"), ("assistant", "Hello")],
            model_family=PromptModelFamily.LLAMA,
        )
        assert request.system_prompt == "You are a helpful assistant."
        assert request.user_prompt == "Hello!"
        assert len(request.conversation_history) == 2
        assert request.model_family == PromptModelFamily.LLAMA


class TestPromptFormatter:
    """Tests for PromptFormatter service."""

    def test_create_formatter_default(self) -> None:
        """Test creating a formatter with default settings."""
        formatter = PromptFormatter()
        assert formatter._default_format == PromptFormat.CHAT_MESSAGES

    def test_create_formatter_custom_default(self) -> None:
        """Test creating a formatter with custom default format."""
        formatter = PromptFormatter(default_format=PromptFormat.INSTRUCTION)
        assert formatter._default_format == PromptFormat.INSTRUCTION

    def test_format_chat_messages_with_system(self) -> None:
        """Test formatting as chat messages with system prompt."""
        formatter = PromptFormatter()
        request = PromptRequest(
            system_prompt="You are a coder.",
            user_prompt="Write hello world",
            model_family=PromptModelFamily.GPT,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.CHAT_MESSAGES
        assert result.is_chat_format is True
        assert result.messages is not None
        assert len(result.messages) == 2
        assert result.messages[0]["role"] == "system"
        assert result.messages[0]["content"] == "You are a coder."
        assert result.messages[1]["role"] == "user"
        assert result.messages[1]["content"] == "Write hello world"

    def test_format_chat_messages_without_system(self) -> None:
        """Test formatting as chat messages without system prompt."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Hello!",
            model_family=PromptModelFamily.GPT,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.CHAT_MESSAGES
        assert result.is_chat_format is True
        assert len(result.messages) == 1
        assert result.messages[0]["role"] == "user"

    def test_format_instruction_with_system(self) -> None:
        """Test formatting as instruction template with system prompt."""
        formatter = PromptFormatter()
        request = PromptRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is 2+2?",
            model_family=PromptModelFamily.LLAMA,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.INSTRUCTION
        assert result.is_chat_format is False
        assert "### Instruction:" in result.content
        assert "You are a helpful assistant." in result.content
        assert "What is 2+2?" in result.content
        assert "### Response:" in result.content

    def test_format_instruction_without_system(self) -> None:
        """Test formatting as instruction template without system prompt."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Tell me a joke.",
            model_family=PromptModelFamily.LLAMA,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.INSTRUCTION
        assert "### Instruction:" in result.content
        assert "Tell me a joke." in result.content
        assert "### Response:" in result.content

    def test_format_code_instruction(self) -> None:
        """Test formatting as code instruction template (DeepSeek-Coder)."""
        formatter = PromptFormatter()
        request = PromptRequest(
            system_prompt="You are an expert Python programmer.",
            user_prompt="Write a function to calculate fibonacci numbers.",
            model_family=PromptModelFamily.DEEPSEEK_CODER,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.CODE_INSTRUCTION
        assert result.is_chat_format is False
        assert "You are an AI programming assistant" in result.content
        assert "You are an expert Python programmer." in result.content
        assert "### Instruction:" in result.content
        assert "Write a function to calculate fibonacci numbers." in result.content
        assert "### Response:" in result.content

    def test_format_completion(self) -> None:
        """Test formatting as simple completion."""
        formatter = PromptFormatter()
        request = PromptRequest(
            system_prompt="You are helpful.",
            user_prompt="Complete this sentence.",
            prompt_format=PromptFormat.COMPLETION,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.COMPLETION
        assert result.is_chat_format is False
        assert "You are helpful." in result.content
        assert "Complete this sentence." in result.content

    def test_explicit_format_overrides_family(self) -> None:
        """Test that explicit format overrides family default."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Test",
            model_family=PromptModelFamily.LLAMA,  # Would default to INSTRUCTION
            prompt_format=PromptFormat.CHAT_MESSAGES,  # Explicit override
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.CHAT_MESSAGES

    def test_normalize_role(self) -> None:
        """Test role name normalization."""
        formatter = PromptFormatter()

        assert formatter._normalize_role("system") == "system"
        assert formatter._normalize_role("user") == "user"
        assert formatter._normalize_role("assistant") == "assistant"
        assert formatter._normalize_role("human") == "user"
        assert formatter._normalize_role("AI") == "assistant"
        assert formatter._normalize_role("bot") == "assistant"
        assert formatter._normalize_role("unknown") == "user"

    def test_format_with_conversation_history(self) -> None:
        """Test formatting with conversation history."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="What about Python?",
            conversation_history=[
                ("user", "What's the best language?"),
                ("assistant", "It depends on your use case."),
            ],
            model_family=PromptModelFamily.GPT,
        )

        result = formatter.format(request)

        assert len(result.messages) == 3
        assert result.messages[0]["role"] == "user"
        assert result.messages[0]["content"] == "What's the best language?"
        assert result.messages[1]["role"] == "assistant"
        assert result.messages[1]["content"] == "It depends on your use case."
        assert result.messages[2]["role"] == "user"
        assert result.messages[2]["content"] == "What about Python?"

    def test_format_for_model_deepseek_coder(self) -> None:
        """Test convenience method for DeepSeek-Coder model."""
        formatter = PromptFormatter()

        result = formatter.format_for_model(
            system_prompt="You are a coder.",
            user_prompt="Write a function.",
            model_name="deepseek-coder-v2:16b",
        )

        assert result.format == PromptFormat.CODE_INSTRUCTION
        assert "You are an AI programming assistant" in result.content

    def test_format_for_model_llama(self) -> None:
        """Test convenience method for Llama model."""
        formatter = PromptFormatter()

        result = formatter.format_for_model(
            system_prompt=None,
            user_prompt="Tell me a story.",
            model_name="llama3.2",
        )

        assert result.format == PromptFormat.INSTRUCTION
        assert "### Instruction:" in result.content

    def test_format_for_model_gpt(self) -> None:
        """Test convenience method for GPT model."""
        formatter = PromptFormatter()

        result = formatter.format_for_model(
            system_prompt="You are helpful.",
            user_prompt="Hello!",
            model_name="gpt-4o",
        )

        assert result.format == PromptFormat.CHAT_MESSAGES
        assert result.is_chat_format is True
        assert len(result.messages) == 2

    def test_get_format_for_model(self) -> None:
        """Test getting format for model name."""
        formatter = PromptFormatter()

        assert (
            formatter.get_format_for_model("deepseek-coder-v2")
            == PromptFormat.CODE_INSTRUCTION
        )
        assert formatter.get_format_for_model("deepseek-r1") == PromptFormat.INSTRUCTION
        assert formatter.get_format_for_model("llama3.2") == PromptFormat.INSTRUCTION
        assert formatter.get_format_for_model("gpt-4o") == PromptFormat.CHAT_MESSAGES
        assert (
            formatter.get_format_for_model("claude-3-opus")
            == PromptFormat.CHAT_MESSAGES
        )
        assert (
            formatter.get_format_for_model("gemini-2.0") == PromptFormat.CHAT_MESSAGES
        )

    def test_unknown_family_uses_default(self) -> None:
        """Test that unknown model family uses default format."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Test",
            model_family=PromptModelFamily.UNKNOWN,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.CHAT_MESSAGES  # Default

    def test_mistral_family_uses_instruction(self) -> None:
        """Test that Mistral family uses instruction format."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Explain quantum computing.",
            model_family=PromptModelFamily.MISTRAL,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.INSTRUCTION

    def test_codestral_family_uses_instruction(self) -> None:
        """Test that Codestral family uses instruction format."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Write a sorting function.",
            model_family=PromptModelFamily.CODESTRAL,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.INSTRUCTION

    def test_phi_family_uses_instruction(self) -> None:
        """Test that Phi family uses instruction format."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="What is AI?",
            model_family=PromptModelFamily.PHI,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.INSTRUCTION

    def test_qwen_family_uses_instruction(self) -> None:
        """Test that Qwen family uses instruction format."""
        formatter = PromptFormatter()
        request = PromptRequest(
            user_prompt="Translate to Spanish.",
            model_family=PromptModelFamily.QWEN,
        )

        result = formatter.format(request)

        assert result.format == PromptFormat.INSTRUCTION


class TestFormattedPrompt:
    """Tests for FormattedPrompt dataclass."""

    def test_to_dict_chat_format(self) -> None:
        """Test converting chat format result to dict."""
        result = FormattedPrompt(
            content="Hello",
            format=PromptFormat.CHAT_MESSAGES,
            is_chat_format=True,
            messages=[{"role": "user", "content": "Hello"}],
        )

        data = result.to_dict()
        assert data["content"] == "Hello"
        assert data["format"] == "chat_messages"
        assert data["is_chat_format"] is True
        assert data["messages"] == [{"role": "user", "content": "Hello"}]

    def test_to_dict_instruction_format(self) -> None:
        """Test converting instruction format result to dict."""
        result = FormattedPrompt(
            content="### Instruction:\nTest\n### Response:",
            format=PromptFormat.INSTRUCTION,
            is_chat_format=False,
            messages=None,
        )

        data = result.to_dict()
        assert data["format"] == "instruction"
        assert data["is_chat_format"] is False
        assert data["messages"] is None


class TestPromptModelFamily:
    """Tests for PromptModelFamily enum."""

    def test_from_model_name_deepseek_coder(self) -> None:
        """Test detecting DeepSeek-Coder family."""
        assert (
            PromptModelFamily.from_model_name("deepseek-coder-v2:16b")
            == PromptModelFamily.DEEPSEEK_CODER
        )
        assert (
            PromptModelFamily.from_model_name("deepseek_coder:33b")
            == PromptModelFamily.DEEPSEEK_CODER
        )
        assert (
            PromptModelFamily.from_model_name("deepseek-coder")
            == PromptModelFamily.DEEPSEEK_CODER
        )

    def test_from_model_name_deepseek(self) -> None:
        """Test detecting DeepSeek family."""
        assert (
            PromptModelFamily.from_model_name("deepseek-r1:32b")
            == PromptModelFamily.DEEPSEEK
        )
        assert (
            PromptModelFamily.from_model_name("deepseek-r1")
            == PromptModelFamily.DEEPSEEK
        )
        assert (
            PromptModelFamily.from_model_name("deepseek") == PromptModelFamily.DEEPSEEK
        )

    def test_from_model_name_llama(self) -> None:
        """Test detecting Llama family."""
        assert PromptModelFamily.from_model_name("llama3.2") == PromptModelFamily.LLAMA
        assert PromptModelFamily.from_model_name("llama3") == PromptModelFamily.LLAMA
        assert (
            PromptModelFamily.from_model_name("llama2:13b") == PromptModelFamily.LLAMA
        )
        assert (
            PromptModelFamily.from_model_name("llama-3-70b") == PromptModelFamily.LLAMA
        )

    def test_from_model_name_mistral(self) -> None:
        """Test detecting Mistral family."""
        assert PromptModelFamily.from_model_name("mistral") == PromptModelFamily.MISTRAL
        assert (
            PromptModelFamily.from_model_name("mistral-7b") == PromptModelFamily.MISTRAL
        )

    def test_from_model_name_codestral(self) -> None:
        """Test detecting Codestral family."""
        assert (
            PromptModelFamily.from_model_name("codestral")
            == PromptModelFamily.CODESTRAL
        )
        assert (
            PromptModelFamily.from_model_name("codestral-latest")
            == PromptModelFamily.CODESTRAL
        )

    def test_from_model_name_phi(self) -> None:
        """Test detecting Phi family."""
        assert PromptModelFamily.from_model_name("phi3") == PromptModelFamily.PHI
        assert PromptModelFamily.from_model_name("phi-3") == PromptModelFamily.PHI
        assert PromptModelFamily.from_model_name("phi3:14b") == PromptModelFamily.PHI

    def test_from_model_name_qwen(self) -> None:
        """Test detecting Qwen family."""
        assert PromptModelFamily.from_model_name("qwen2.5:7b") == PromptModelFamily.QWEN
        assert PromptModelFamily.from_model_name("qwen-14b") == PromptModelFamily.QWEN

    def test_from_model_name_gpt(self) -> None:
        """Test detecting GPT family."""
        assert PromptModelFamily.from_model_name("gpt-4o") == PromptModelFamily.GPT
        assert PromptModelFamily.from_model_name("gpt-4-turbo") == PromptModelFamily.GPT
        assert (
            PromptModelFamily.from_model_name("gpt-3.5-turbo") == PromptModelFamily.GPT
        )

    def test_from_model_name_claude(self) -> None:
        """Test detecting Claude family."""
        assert (
            PromptModelFamily.from_model_name("claude-3-opus-20240229")
            == PromptModelFamily.CLAUDE
        )
        assert (
            PromptModelFamily.from_model_name("claude-3.5-sonnet")
            == PromptModelFamily.CLAUDE
        )

    def test_from_model_name_gemini(self) -> None:
        """Test detecting Gemini family."""
        assert (
            PromptModelFamily.from_model_name("gemini-2.0-flash")
            == PromptModelFamily.GEMINI
        )
        assert (
            PromptModelFamily.from_model_name("gemini-1.5-pro")
            == PromptModelFamily.GEMINI
        )

    def test_from_model_name_unknown(self) -> None:
        """Test detecting unknown family."""
        assert (
            PromptModelFamily.from_model_name("unknown-model")
            == PromptModelFamily.UNKNOWN
        )
        assert (
            PromptModelFamily.from_model_name("random-name")
            == PromptModelFamily.UNKNOWN
        )

    def test_default_prompt_format(self) -> None:
        """Test default prompt format per family."""
        assert (
            PromptModelFamily.DEEPSEEK_CODER.default_prompt_format
            == PromptFormat.CODE_INSTRUCTION
        )
        assert (
            PromptModelFamily.DEEPSEEK.default_prompt_format == PromptFormat.INSTRUCTION
        )
        assert PromptModelFamily.LLAMA.default_prompt_format == PromptFormat.INSTRUCTION
        assert (
            PromptModelFamily.MISTRAL.default_prompt_format == PromptFormat.INSTRUCTION
        )
        assert (
            PromptModelFamily.CODESTRAL.default_prompt_format
            == PromptFormat.INSTRUCTION
        )
        assert PromptModelFamily.PHI.default_prompt_format == PromptFormat.INSTRUCTION
        assert PromptModelFamily.QWEN.default_prompt_format == PromptFormat.INSTRUCTION
        assert PromptModelFamily.GPT.default_prompt_format == PromptFormat.CHAT_MESSAGES
        assert (
            PromptModelFamily.CLAUDE.default_prompt_format == PromptFormat.CHAT_MESSAGES
        )
        assert (
            PromptModelFamily.GEMINI.default_prompt_format == PromptFormat.CHAT_MESSAGES
        )


class TestCreatePromptFormatter:
    """Tests for prompt_formatter factory function."""

    def test_factory_default(self) -> None:
        """Test factory with default parameters."""
        formatter = create_prompt_formatter()
        assert isinstance(formatter, PromptFormatter)
        assert formatter._default_format == PromptFormat.CHAT_MESSAGES

    def test_factory_custom(self) -> None:
        """Test factory with custom default format."""
        formatter = create_prompt_formatter(default_format=PromptFormat.INSTRUCTION)
        assert isinstance(formatter, PromptFormatter)
        assert formatter._default_format == PromptFormat.INSTRUCTION
