from __future__ import annotations

from typing import Any

import httpx

from video_agent.adapters.llm.script_sanitizer import sanitize_script_text


class ProviderError(RuntimeError):
    """Base class for normalized upstream provider failures."""


class ProviderAuthError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        max_retries: int = 0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.http_client = http_client or httpx.Client(timeout=timeout_seconds)

    def generate_script(self, prompt_text: str) -> str:
        last_error: ProviderError | None = None
        for _attempt in range(self.max_retries + 1):
            try:
                response = self.http_client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Return only runnable Manim Python code."},
                            {"role": "user", "content": prompt_text},
                        ],
                        "temperature": 0,
                    },
                    timeout=self.timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                last_error = ProviderTimeoutError(str(exc) or "Provider request timed out")
                continue
            except httpx.HTTPError as exc:
                raise ProviderResponseError(str(exc) or "Provider request failed") from exc

            if response.status_code == 401:
                raise ProviderAuthError(self._extract_error_message(response, "Provider authentication failed"))
            if response.status_code == 429:
                last_error = ProviderRateLimitError(self._extract_error_message(response, "Provider rate limited request"))
                continue
            if response.status_code >= 400:
                raise ProviderResponseError(self._extract_error_message(response, "Provider returned an error response"))

            try:
                payload = response.json()
            except ValueError as exc:
                raise ProviderResponseError("Provider returned invalid JSON") from exc

            content = sanitize_script_text(self._extract_content(payload))
            if not content.strip():
                raise ProviderResponseError("Provider returned empty completion content")
            return content

        if last_error is not None:
            raise last_error
        raise ProviderResponseError("Provider request failed without a result")

    @staticmethod
    def _extract_error_message(response: httpx.Response, default: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return default

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"]
        return default


    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderResponseError("Provider response did not include choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ProviderResponseError("Provider response choice was malformed")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ProviderResponseError("Provider response did not include a message")

        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
            return "\n".join(text_parts)
        raise ProviderResponseError("Provider response content was malformed")
