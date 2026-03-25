from __future__ import annotations

from importlib import import_module
from typing import Any

from video_agent.adapters.llm.client import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from video_agent.adapters.llm.script_sanitizer import sanitize_script_text


class LiteLLMClient:
    def __init__(
        self,
        *,
        model: str,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 60,
        max_retries: int = 0,
        litellm_module: Any | None = None,
    ) -> None:
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._litellm_module = litellm_module

    def generate_script(self, prompt_text: str) -> str:
        try:
            response = self._get_litellm_module().completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Return only runnable Manim Python code."},
                    {"role": "user", "content": prompt_text},
                ],
                api_base=self.api_base,
                api_key=self.api_key,
                timeout=self.timeout_seconds,
                num_retries=self.max_retries,
                temperature=0,
                drop_params=True,
            )
        except Exception as exc:
            raise self._normalize_error(exc) from exc

        content = sanitize_script_text(self._extract_content(response))
        if not content.strip():
            raise ProviderResponseError("Provider returned empty completion content")
        return content

    def _get_litellm_module(self) -> Any:
        if self._litellm_module is None:
            try:
                self._litellm_module = import_module("litellm")
            except ImportError as exc:
                raise ProviderResponseError("LiteLLM is not installed") from exc
        return self._litellm_module

    def _normalize_error(self, exc: Exception) -> ProviderResponseError:
        litellm_module = self._get_litellm_module()
        if self._isinstance(exc, litellm_module, "AuthenticationError"):
            return ProviderAuthError(str(exc) or "Provider authentication failed")
        if self._isinstance(exc, litellm_module, "RateLimitError"):
            return ProviderRateLimitError(str(exc) or "Provider rate limited request")
        if self._isinstance(exc, litellm_module, "Timeout", "TimeoutError"):
            return ProviderTimeoutError(str(exc) or "Provider request timed out")
        return ProviderResponseError(str(exc) or "Provider request failed")

    @classmethod
    def _isinstance(cls, exc: Exception, module: Any, *names: str) -> bool:
        types = tuple(
            value
            for name in names
            if isinstance(value := getattr(module, name, None), type)
        )
        return bool(types) and isinstance(exc, types)

    @classmethod
    def _extract_content(cls, payload: Any) -> str:
        choices = cls._lookup(payload, "choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderResponseError("Provider response did not include choices")

        message = cls._lookup(choices[0], "message")
        if message is None:
            raise ProviderResponseError("Provider response did not include a message")

        content = cls._lookup(message, "content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if cls._lookup(item, "type") == "text" and isinstance(text := cls._lookup(item, "text"), str):
                    text_parts.append(text)
            return "\n".join(text_parts)
        raise ProviderResponseError("Provider response content was malformed")

    @staticmethod
    def _lookup(value: Any, key: str) -> Any:
        if isinstance(value, dict):
            return value.get(key)
        return getattr(value, key, None)
