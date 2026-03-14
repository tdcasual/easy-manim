from video_agent.validation.static_check import StaticCheckValidator



def test_static_check_blocks_subprocess_usage() -> None:
    code = "import subprocess\nsubprocess.run(['rm', '-rf', '/'])"
    report = StaticCheckValidator().validate(code)
    assert report.passed is False
    assert report.issues[0].code == "forbidden_import"


def test_static_check_accepts_scene_subclasses_beyond_base_scene() -> None:
    code = (
        "from manim import MovingCameraScene\n\n"
        "class GeneratedScene(MovingCameraScene):\n"
        "    def construct(self):\n"
        "        pass\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is True


def test_static_check_blocks_transformmatchingtex_numeric_slice_source() -> None:
    code = (
        "from manim import MathTex, Scene, TransformMatchingTex\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        expr = MathTex(r'x = \\\\frac{-b \\\\pm \\\\sqrt{b^2 - 4ac}}{2a}')\n"
        "        part = MathTex(r'b^2 - 4ac')\n"
        "        self.play(TransformMatchingTex(expr[0][9:18].copy(), part))\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "unsafe_transformmatchingtex_slice"


def test_static_check_allows_transformmatchingtex_between_full_expressions() -> None:
    code = (
        "from manim import MathTex, Scene, TransformMatchingTex\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        old_expr = MathTex(r'x^2 + 2x + 1')\n"
        "        new_expr = MathTex(r'(x + 1)^2')\n"
        "        self.play(TransformMatchingTex(old_expr, new_expr))\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is True


def test_static_check_blocks_non_animation_method_calls_inside_play() -> None:
    code = (
        "from manim import MathTex, RED, Scene, Indicate\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex('a^2 + b^2 = c^2')\n"
        "        line = formula.copy()\n"
        "        self.play(Indicate(line), formula.set_color_by_tex('c^2', RED))\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "non_animation_play_argument"


def test_static_check_blocks_plain_mobject_constructors_inside_play() -> None:
    code = (
        "from manim import MathTex, RED, Scene, SurroundingRectangle\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex('a^2 + b^2 = c^2')\n"
        "        self.play(formula[4].animate.set_color(RED), SurroundingRectangle(formula[4], color=RED))\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "non_animation_play_argument"


def test_static_check_blocks_tex_for_symbolic_math_labels() -> None:
    code = (
        "from manim import Axes, BLACK, Scene, Tex\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        axes.x_axis.add_labels({3.14: Tex(r'\\\\pi', color=BLACK)})\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "tex_math_label"


def test_static_check_blocks_set_backstroke_width_keyword() -> None:
    code = (
        "from manim import MathTex, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        label = MathTex('y = x').set_backstroke(width=5)\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "set_backstroke_width_keyword"


def test_static_check_blocks_bare_tex_control_sequence_highlights() -> None:
    code = (
        "from manim import MathTex, Scene, SurroundingRectangle\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex(r'd = \\\\sqrt{x}')\n"
        "        marker = SurroundingRectangle(formula.get_part_by_tex(r'\\\\sqrt'))\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    issue_codes = {issue.code for issue in report.issues}

    assert "unsafe_bare_tex_highlight" in issue_codes
    assert "unsafe_bare_tex_selection" in issue_codes


def test_static_check_blocks_alias_based_bare_tex_control_sequence_highlights() -> None:
    code = (
        "from manim import MathTex, Scene, SurroundingRectangle\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex(r'd = \\\\sqrt{x}')\n"
        "        sqrt_term = formula.get_part_by_tex(r'\\\\sqrt')\n"
        "        marker = SurroundingRectangle(sqrt_term)\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    issue_codes = {issue.code for issue in report.issues}

    assert "unsafe_bare_tex_highlight" in issue_codes
    assert "unsafe_bare_tex_selection" in issue_codes


def test_static_check_blocks_nonexistent_axis_label_getters() -> None:
    code = (
        "from manim import Axes, MathTex, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        labels = axes.get_x_axis_labels(MathTex('0'), MathTex('1'))\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "nonexistent_axis_label_getter"


def test_static_check_blocks_bare_tex_control_sequence_source_selection() -> None:
    code = (
        "from manim import MathTex, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        formula = MathTex(r'd = \\\\sqrt{x}')\n"
        "        sqrt_term = formula.get_part_by_tex(r'\\\\sqrt')\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "unsafe_bare_tex_selection"


def test_static_check_blocks_nonexistent_graph_area_getters() -> None:
    code = (
        "from manim import Axes, BLUE, Scene\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        axes = Axes()\n"
        "        graph = axes.plot(lambda x: x, color=BLUE)\n"
        "        area = axes.get_area_under_graph(graph, x_range=[0, 1])\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "nonexistent_graph_area_getter"


def test_static_check_blocks_unsupported_diagonal_corner_getters() -> None:
    code = (
        "from manim import Polygon, Scene, ORIGIN, RIGHT, UP\n\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        triangle = Polygon(ORIGIN, RIGHT * 3, UP * 4)\n"
        "        point = triangle.get_bottom_right()\n"
    )

    report = StaticCheckValidator().validate(code)

    assert report.passed is False
    assert report.issues[0].code == "unsupported_diagonal_corner_getter"
