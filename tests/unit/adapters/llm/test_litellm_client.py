from types import SimpleNamespace

import pytest

from video_agent.adapters.llm.client import ProviderAuthError
from video_agent.adapters.llm.litellm_client import LiteLLMClient


def test_litellm_client_calls_completion_with_expected_kwargs() -> None:
    captured: dict[str, object] = {}

    def completion(**kwargs) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "content": "from manim import Scene\nclass GeneratedScene(Scene):\n    pass\n",
                    }
                }
            ]
        }

    client = LiteLLMClient(
        model="openai/gpt-4.1-mini",
        api_base="https://example.test/v1",
        api_key="secret",
        timeout_seconds=12,
        max_retries=3,
        litellm_module=SimpleNamespace(completion=completion),
    )

    script = client.generate_script("draw a circle")

    assert "GeneratedScene" in script
    assert captured["model"] == "openai/gpt-4.1-mini"
    assert captured["api_base"] == "https://example.test/v1"
    assert captured["api_key"] == "secret"
    assert captured["timeout"] == 12
    assert captured["num_retries"] == 3
    assert captured["temperature"] == 0
    assert captured["drop_params"] is True
    assert captured["messages"] == [
        {"role": "system", "content": "Return only runnable Manim Python code."},
        {"role": "user", "content": "draw a circle"},
    ]


def test_litellm_client_maps_auth_errors() -> None:
    class AuthenticationError(Exception):
        pass

    def completion(**kwargs) -> dict[str, object]:
        raise AuthenticationError("bad key")

    client = LiteLLMClient(
        model="openai/gpt-4.1-mini",
        litellm_module=SimpleNamespace(
            completion=completion,
            AuthenticationError=AuthenticationError,
        ),
    )

    with pytest.raises(ProviderAuthError, match="bad key"):
        client.generate_script("draw a circle")


def test_litellm_client_sanitizes_fenced_code() -> None:
    def completion(**kwargs) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "Here is the Manim script:\n\n"
                            "```python\n"
                            "from manim import Scene\n\n"
                            "class GeneratedScene(Scene):\n"
                            "    pass\n"
                            "```"
                        )
                    }
                }
            ]
        }

    client = LiteLLMClient(
        model="openai/gpt-4.1-mini",
        litellm_module=SimpleNamespace(completion=completion),
    )

    script = client.generate_script("draw a circle")

    assert script.startswith("from manim import Scene")
    assert "```" not in script
