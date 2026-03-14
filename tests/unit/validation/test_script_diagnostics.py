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


def test_script_diagnostics_accepts_moving_camera_scene_subclass() -> None:
    script = (
        "from manim import MovingCameraScene\n\n"
        "class Demo(MovingCameraScene):\n"
        "    def construct(self):\n"
        "        pass\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert diagnostics == []


def test_script_diagnostics_flags_unsafe_transformmatchingtex_slice() -> None:
    script = (
        "from manim import MathTex, Scene, TransformMatchingTex\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        expr = MathTex(r'x = \\\\frac{-b \\\\pm \\\\sqrt{b^2 - 4ac}}{2a}')\n"
        "        part = MathTex(r'b^2 - 4ac')\n"
        "        self.play(TransformMatchingTex(expr[0][9:18].copy(), part))\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "unsafe_transformmatchingtex_slice"
    assert diagnostics[0].call_name == "TransformMatchingTex"


def test_script_diagnostics_flags_non_animation_method_calls_inside_play() -> None:
    script = (
        "from manim import MathTex, RED, Scene, Indicate\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex('a^2 + b^2 = c^2')\n"
        "        line = formula.copy()\n"
        "        self.play(Indicate(line), formula.set_color_by_tex('c^2', RED))\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "non_animation_play_argument"
    assert diagnostics[0].line == 7
    assert diagnostics[0].call_name == "set_color_by_tex"


def test_script_diagnostics_flags_plain_mobject_constructors_inside_play() -> None:
    script = (
        "from manim import MathTex, RED, Scene, SurroundingRectangle\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex('a^2 + b^2 = c^2')\n"
        "        self.play(formula[4].animate.set_color(RED), SurroundingRectangle(formula[4], color=RED))\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "non_animation_play_argument"
    assert diagnostics[0].line == 6
    assert diagnostics[0].call_name == "SurroundingRectangle"


def test_script_diagnostics_flags_tex_used_for_symbolic_math_labels() -> None:
    script = (
        "from manim import Axes, BLACK, Scene, Tex\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        axes.x_axis.add_labels({3.14: Tex(r'\\\\pi', color=BLACK)})\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "tex_math_label"
    assert diagnostics[0].line == 6
    assert diagnostics[0].call_name == "Tex"


def test_script_diagnostics_flags_set_backstroke_width_keyword() -> None:
    script = (
        "from manim import MathTex, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        label = MathTex('y = x').set_backstroke(width=5)\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "set_backstroke_width_keyword"
    assert diagnostics[0].line == 5
    assert diagnostics[0].call_name == "set_backstroke"
    assert diagnostics[0].keywords == ["width"]


def test_script_diagnostics_flags_bare_tex_control_sequence_highlights() -> None:
    script = (
        "from manim import MathTex, Scene, SurroundingRectangle\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex(r'd = \\\\sqrt{x}')\n"
        "        marker = SurroundingRectangle(formula.get_part_by_tex(r'\\\\sqrt'))\n"
    )

    diagnostics = collect_script_diagnostics(script)

    codes = {diagnostic.code for diagnostic in diagnostics}

    assert "unsafe_bare_tex_highlight" in codes
    assert "unsafe_bare_tex_selection" in codes


def test_script_diagnostics_flags_alias_based_bare_tex_control_sequence_highlights() -> None:
    script = (
        "from manim import MathTex, Scene, SurroundingRectangle\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex(r'd = \\\\sqrt{x}')\n"
        "        sqrt_term = formula.get_part_by_tex(r'\\\\sqrt')\n"
        "        marker = SurroundingRectangle(sqrt_term)\n"
    )

    diagnostics = collect_script_diagnostics(script)

    codes = {diagnostic.code for diagnostic in diagnostics}

    assert "unsafe_bare_tex_highlight" in codes
    assert "unsafe_bare_tex_selection" in codes


def test_script_diagnostics_flags_nonexistent_axis_label_getters() -> None:
    script = (
        "from manim import Axes, MathTex, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        labels = axes.get_x_axis_labels(MathTex('0'), MathTex('1'))\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "nonexistent_axis_label_getter"
    assert diagnostics[0].line == 6
    assert diagnostics[0].call_name == "get_x_axis_labels"


def test_script_diagnostics_flags_bare_tex_control_sequence_source_selection() -> None:
    script = (
        "from manim import MathTex, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex(r'd = \\\\sqrt{x}')\n"
        "        sqrt_term = formula.get_part_by_tex(r'\\\\sqrt')\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "unsafe_bare_tex_selection"
    assert diagnostics[0].line == 6
    assert diagnostics[0].call_name == "get_part_by_tex"


def test_script_diagnostics_flags_nonexistent_graph_area_getters() -> None:
    script = (
        "from manim import Axes, BLUE, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        graph = axes.plot(lambda x: x, color=BLUE)\n"
        "        area = axes.get_area_under_graph(graph, x_range=[0, 1])\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "nonexistent_graph_area_getter"
    assert diagnostics[0].line == 7
    assert diagnostics[0].call_name == "get_area_under_graph"


def test_script_diagnostics_flags_unsupported_diagonal_corner_getters() -> None:
    script = (
        "from manim import Polygon, Scene, ORIGIN, RIGHT, UP\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        triangle = Polygon(ORIGIN, RIGHT * 3, UP * 4)\n"
        "        point = triangle.get_bottom_right()\n"
    )

    diagnostics = collect_script_diagnostics(script)

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "unsupported_diagonal_corner_getter"
    assert diagnostics[0].line == 6
    assert diagnostics[0].call_name == "get_bottom_right"
