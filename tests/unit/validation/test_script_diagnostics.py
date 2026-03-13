from video_agent.validation.script_diagnostics import collect_script_diagnostics


def test_script_diagnostics_flags_unsupported_helper_kwargs() -> None:
    script = (
        "from manim import Axes, RED, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        point_a = axes.c2p(1, 2)\n"
        "        helper = axes.get_v_line(point_a, color=RED, opacity=0.5)\n"
        "        self.add(axes, helper)\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "unsupported_helper_kwargs"
    assert diagnostics[0].line == 7
    assert diagnostics[0].call_name == "get_v_line"
    assert diagnostics[0].keywords == ["color", "opacity"]


def test_script_diagnostics_flags_missing_scene_subclass() -> None:
    diagnostics = collect_script_diagnostics("from manim import Circle\ncircle = Circle()\n")

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "missing_scene_subclass"


def test_script_diagnostics_flags_chained_coordinate_method_calls() -> None:
    script = (
        "from manim import Axes, RED, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        bad = axes.c2p(1, 2).set_color(RED)\n"
        "        self.add(axes)\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "coordinate_object_method_call"
    assert diagnostics[0].helper_name == "c2p"
    assert diagnostics[0].call_name == "set_color"
