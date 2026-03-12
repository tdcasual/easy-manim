from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def generate_script(self, prompt_text: str) -> str:
        ...


class StubLLMClient:
    def __init__(self, script: str | None = None) -> None:
        self.script = script or (
            "from manim import Circle, Create, Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle()\n"
            "        self.play(Create(circle))\n"
        )

    def generate_script(self, prompt_text: str) -> str:
        return self.script
