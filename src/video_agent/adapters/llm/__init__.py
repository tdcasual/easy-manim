"""LLM adapters."""

from video_agent.adapters.llm.client import LLMClient, StubLLMClient
from video_agent.adapters.llm.openai_compatible_client import (
    OpenAICompatibleLLMClient,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)

__all__ = [
    "LLMClient",
    "StubLLMClient",
    "OpenAICompatibleLLMClient",
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderTimeoutError",
    "ProviderResponseError",
]
