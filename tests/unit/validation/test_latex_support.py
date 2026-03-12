from video_agent.validation.latex_support import script_uses_latex


def test_script_uses_latex_detects_mathtex_and_tex_calls() -> None:
    assert (
        script_uses_latex(
            "from manim import MathTex, Scene\n\n"
            "class Demo(Scene):\n"
            "    def construct(self):\n"
            "        self.add(MathTex(r'x^2'))\n"
        )
        is True
    )
    assert (
        script_uses_latex(
            "import manim as mn\n\n"
            "class Demo(mn.Scene):\n"
            "    def construct(self):\n"
            "        self.add(mn.Tex('hello'))\n"
        )
        is True
    )


def test_script_uses_latex_ignores_plain_text_scripts() -> None:
    assert (
        script_uses_latex(
            "from manim import Circle, Scene\n\n"
            "class Demo(Scene):\n"
            "    def construct(self):\n"
            "        self.add(Circle())\n"
        )
        is False
    )
