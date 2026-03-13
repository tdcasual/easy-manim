from pathlib import Path

from video_agent.validation.runtime_smoke import run_mathtex_smoke


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def test_mathtex_smoke_reports_success_when_tex_pipeline_writes_svg(tmp_path: Path) -> None:
    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_executable(
        fake_latex,
        "#!/bin/sh\n"
        "printf 'dvi' > smoke.dvi\n",
    )
    _write_executable(
        fake_dvisvgm,
        "#!/bin/sh\n"
        "printf 'svg' > smoke.svg\n",
    )

    result = run_mathtex_smoke(
        work_dir=tmp_path,
        latex_command=str(fake_latex),
        dvisvgm_command=str(fake_dvisvgm),
    )

    assert result.available is True
    assert result.error is None


def test_mathtex_smoke_reports_failure_details_when_svg_conversion_fails(tmp_path: Path) -> None:
    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_executable(
        fake_latex,
        "#!/bin/sh\n"
        "printf 'dvi' > smoke.dvi\n",
    )
    _write_executable(
        fake_dvisvgm,
        "#!/bin/sh\n"
        "printf 'dvisvgm failed' >&2\n"
        "exit 7\n",
    )

    result = run_mathtex_smoke(
        work_dir=tmp_path,
        latex_command=str(fake_latex),
        dvisvgm_command=str(fake_dvisvgm),
    )

    assert result.available is False
    assert "dvisvgm failed" in result.error.lower()
