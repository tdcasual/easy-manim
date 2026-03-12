import httpx
import pytest

from video_agent.adapters.llm.openai_compatible_client import (
    OpenAICompatibleLLMClient,
    ProviderAuthError,
)


def test_openai_compatible_client_returns_first_message_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://example.test/v1/chat/completions")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "from manim import Scene\nclass GeneratedScene(Scene):\n    pass\n"}}
                ]
            },
        )

    client = OpenAICompatibleLLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        model="gpt-4.1-mini",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert "GeneratedScene" in client.generate_script("draw a circle")



def test_openai_compatible_client_raises_normalized_error_on_401() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = OpenAICompatibleLLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        model="gpt-4.1-mini",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ProviderAuthError):
        client.generate_script("draw a circle")


def test_openai_compatible_client_strips_markdown_code_fence() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "```python\nfrom manim import Scene\n\nclass GeneratedScene(Scene):\n    pass\n```"
                        }
                    }
                ]
            },
        )

    client = OpenAICompatibleLLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        model="gpt-4.1-mini",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.generate_script("draw a circle").startswith("from manim import Scene")


def test_openai_compatible_client_extracts_fenced_code_from_wrapped_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Here is the Manim script:\n\n```python\nfrom manim import Scene\n\nclass GeneratedScene(Scene):\n    pass\n```"
                        }
                    }
                ]
            },
        )

    client = OpenAICompatibleLLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        model="gpt-4.1-mini",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    script = client.generate_script("draw a circle")

    assert script.startswith("from manim import Scene")
    assert "```" not in script
