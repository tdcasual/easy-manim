from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def generate_script(self, prompt_text: str) -> str:
        ...


class StubLLMClient:
    def __init__(self, script: str | None = None) -> None:
        self.script = script

    def generate_script(self, prompt_text: str) -> str:
        if self.script is not None:
            return self.script

        text = prompt_text.lower()
        if "formula strategy: mathtex_focus" in text or any(keyword in text for keyword in ("quadratic formula", "equation", "discriminant")):
            return _formula_stub_script()
        if "scene class: movingcamerascene" in text or any(keyword in text for keyword in ("axis", "graph", "coordinate", "point")):
            return _graph_stub_script()
        return _shape_stub_script()


def _shape_stub_script() -> str:
    return (
        "from manim import BLACK, BLUE, Circle, Create, DOWN, FadeIn, Scene, Text, UP, config\n\n"
        "config.background_color = '#F7F4EA'\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        title = Text('Main Idea', font_size=34, color=BLACK).to_edge(UP)\n"
        "        circle = Circle(color=BLUE)\n"
        "        label = Text('Highlighted shape', font_size=24, color=BLACK).next_to(circle, DOWN)\n"
        "        self.add(title)\n"
        "        self.play(Create(circle), FadeIn(label))\n"
        "        self.wait(0.2)\n"
    )


def _graph_stub_script() -> str:
    return (
        "from manim import Axes, BLACK, Create, Dot, FadeIn, MovingCameraScene, RIGHT, Text, UP, YELLOW, config\n\n"
        "config.background_color = '#F7F4EA'\n\n"
        "class GeneratedScene(MovingCameraScene):\n"
        "    def construct(self):\n"
        "        title = Text('Coordinate Focus', font_size=34, color=BLACK).to_edge(UP)\n"
        "        axes = Axes(\n"
        "            x_range=[0, 4, 1],\n"
        "            y_range=[0, 4, 1],\n"
        "            x_length=6,\n"
        "            y_length=4,\n"
        "            axis_config={'color': BLACK},\n"
        "        )\n"
        "        point = Dot(axes.c2p(2, 2), color=YELLOW)\n"
        "        label = Text('Midpoint', font_size=24, color=BLACK).next_to(point, RIGHT)\n"
        "        self.add(title)\n"
        "        self.play(Create(axes), FadeIn(point), FadeIn(label))\n"
        "        self.play(self.camera.frame.animate.move_to(point).scale(0.85))\n"
        "        self.wait(0.2)\n"
    )


def _formula_stub_script() -> str:
    return (
        "from manim import BLACK, DOWN, FadeIn, Scene, SurroundingRectangle, Text, UP, YELLOW, config\n\n"
        "config.background_color = '#F7F4EA'\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        "        title = Text('Quadratic Formula', font_size=34, color=BLACK).to_edge(UP)\n"
        "        formula = Text('x = (-b +/- sqrt(b^2 - 4ac)) / 2a', font_size=28, color=BLACK)\n"
        "        note = Text('Focus on the discriminant', font_size=24, color=BLACK).next_to(formula, DOWN)\n"
        "        focus = SurroundingRectangle(formula, buff=0.15, color=YELLOW)\n"
        "        self.add(title, formula)\n"
        "        self.play(FadeIn(note), FadeIn(focus))\n"
        "        self.wait(0.2)\n"
    )
