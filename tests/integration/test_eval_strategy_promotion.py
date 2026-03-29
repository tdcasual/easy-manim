import json
from pathlib import Path

from video_agent.application.eval_service import EvaluationService
from video_agent.config import Settings
from video_agent.domain.strategy_models import StrategyProfile
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_eval_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            eval_root=data_dir / "evals",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
        )
    )


def _suite_path() -> Path:
    return Path(__file__).resolve().parents[2] / "evals" / "beta_prompt_suite.json"


def test_eval_service_runs_challenger_and_records_strategy_metrics(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_eval_settings(tmp_path))
    strategy = app_context.store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-1",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
            params={"style_hints": {"tone": "teaching"}},
        )
    )
    service = EvaluationService(app_context)

    result = service.run_strategy_challenger(
        suite_path=str(_suite_path()),
        challenger_profile=strategy,
        limit=1,
    )

    assert result["baseline"]["total_cases"] == 1
    assert result["challenger"]["total_cases"] == 1

    profiles = app_context.store.list_strategy_profiles()
    assert len(profiles) == 1
    assert profiles[0].metrics["last_eval_run"]["challenger_run_id"] == result["challenger"]["run_id"]
    assert "promotion_recommended" in profiles[0].metrics["last_eval_run"]


def test_eval_service_includes_scene_spec_signals_in_eval_items(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_eval_settings(tmp_path))
    service = EvaluationService(app_context)
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "suite_id": "scene-spec-signal-suite",
                "cases": [
                    {"case_id": "signal-case", "prompt": "draw a blue circle", "tags": ["smoke"]},
                ],
            }
        )
    )

    summary = service.run_suite(
        suite_path=str(suite_path),
        profile_patch={"style_hints": {"scene_complexity": "high", "animation_density": "high"}},
    )

    assert len(summary.items) == 1
    item = summary.items[0]
    assert "requested_scene_complexity:high" in item.risk_signals
    assert "animation_density:high" in item.risk_signals
    assert isinstance(item.capability_gate_signals, list)
