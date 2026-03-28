import json
from collections.abc import Callable
from pathlib import Path
import sys
import types

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from tests.support import bootstrapped_settings


def _with_temporary_mcp_shim(fn: Callable[[], object]) -> object:
    if "mcp.server.fastmcp" in sys.modules:
        return fn()

    injected: dict[str, types.ModuleType] = {}
    original: dict[str, types.ModuleType] = {}
    module_names = ("mcp", "mcp.server", "mcp.server.fastmcp")
    for name in module_names:
        module = sys.modules.get(name)
        if module is not None:
            original[name] = module

    mcp_module = types.ModuleType("mcp")
    mcp_server_module = types.ModuleType("mcp.server")
    mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")

    class _Context:  # pragma: no cover - import shim
        pass

    mcp_fastmcp_module.Context = _Context
    mcp_server_module.fastmcp = mcp_fastmcp_module
    mcp_module.server = mcp_server_module

    injected["mcp"] = mcp_module
    injected["mcp.server"] = mcp_server_module
    injected["mcp.server.fastmcp"] = mcp_fastmcp_module

    try:
        sys.modules.update(injected)
        return fn()
    finally:
        for name in module_names:
            previous = original.get(name)
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def _create_http_api(settings: Settings):
    def _load():
        from video_agent.server.http_api import create_http_api

        return create_http_api(settings)

    return _with_temporary_mcp_shim(_load)


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_http_reliability_settings(tmp_path: Path) -> Settings:
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
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            auth_mode="required",
            multi_agent_workflow_enabled=True,
        )
    )


def _build_http_preview_failure_settings(tmp_path: Path) -> Settings:
    settings = _build_http_reliability_settings(tmp_path)

    fake_ffmpeg = tmp_path / "fake_ffmpeg_blank.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "python - \"$6\" <<'PY'\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "import sys\n"
        "pattern = Path(sys.argv[1])\n"
        "pattern.parent.mkdir(parents=True, exist_ok=True)\n"
        "for index in (1, 2):\n"
        "    Image.new('RGB', (320, 180), (0, 0, 0)).save(pattern.parent / f'frame_{index:03d}.png')\n"
        "PY\n",
    )
    settings.ffmpeg_command = str(fake_ffmpeg)
    return settings


def _seed_agent(client: TestClient, agent_id: str, secret: str) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(AgentProfile(agent_id=agent_id, name=agent_id))
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def _login(client: TestClient, secret: str) -> str:
    response = client.post("/api/sessions", json={"agent_token": secret})
    assert response.status_code == 200
    return response.json()["session_token"]


def _create_task_and_run_worker(client: TestClient, token: str, prompt: str) -> str:
    created = client.post(
        "/api/tasks",
        json={"prompt": prompt},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    client.app.state.app_context.worker.run_once()
    return task_id


def test_http_task_reliability_endpoints_expose_scene_spec_and_quality_score(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_reliability_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    token = _login(client, "agent-a-secret")
    task_id = _create_task_and_run_worker(client, token, "draw a blue circle and label the radius")

    scene_spec = client.get(
        f"/api/tasks/{task_id}/scene-spec",
        headers={"Authorization": f"Bearer {token}"},
    )
    quality = client.get(
        f"/api/tasks/{task_id}/quality-score",
        headers={"Authorization": f"Bearer {token}"},
    )
    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert scene_spec.status_code == 200
    assert scene_spec.json()["summary"]
    assert quality.status_code == 200
    assert "total_score" in quality.json()
    assert bundle.status_code == 200
    assert bundle.json()["scene_spec"] is not None
    assert bundle.json()["quality_scorecard"] is not None
    assert bundle.json()["quality_gate_status"] == "accepted"


def test_http_task_reliability_endpoints_expose_recovery_plan(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_preview_failure_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    token = _login(client, "agent-a-secret")
    task_id = _create_task_and_run_worker(client, token, "draw a circle")

    recovery = client.get(
        f"/api/tasks/{task_id}/recovery-plan",
        headers={"Authorization": f"Bearer {token}"},
    )
    bundle = client.get(
        f"/api/tasks/{task_id}/review-bundle",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert recovery.status_code == 200
    assert recovery.json()["selected_action"] == "preview_repair"
    assert bundle.status_code == 200
    assert bundle.json()["recovery_plan"] is not None
    assert bundle.json()["recovery_plan"]["selected_action"] == "preview_repair"


def test_http_accept_best_marks_task_snapshot(tmp_path: Path) -> None:
    client = TestClient(_create_http_api(_build_http_reliability_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    token = _login(client, "agent-a-secret")
    task_id = _create_task_and_run_worker(client, token, "draw a blue circle")

    accepted = client.post(
        f"/api/tasks/{task_id}/accept-best",
        headers={"Authorization": f"Bearer {token}"},
    )
    snapshot = client.get(
        f"/api/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert accepted.status_code == 200
    assert accepted.json()["accepted_as_best"] is True
    assert snapshot.status_code == 200
    assert snapshot.json()["accepted_as_best"] is True
    assert snapshot.json()["accepted_version_rank"] == 1
