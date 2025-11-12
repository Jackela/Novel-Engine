#!/usr/bin/env python3
"""
AI Gateway Provider Implementations

Concrete implementations of LLM providers for different AI services
including OpenAI, Ollama, and other major providers.

Each provider implements the ILLMProvider interface and handles:
- Authentication and API communication
- Request/response mapping and transformation
- Error handling and status mapping
- Model capability detection and validation
- Token estimation and cost calculation
"""

from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

__all__ = ["OpenAIProvider", "OllamaProvider"]
