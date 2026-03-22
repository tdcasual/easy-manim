from pathlib import Path

from scripts.beta_smoke import run_beta_smoke



def test_streamable_http_single_task_flow(tmp_path: Path) -> None:
    summary = run_beta_smoke(tmp_path)

    assert summary["task_id"]
    assert summary["snapshot"]["status"] == "completed"
    assert summary["result"]["ready"] is True
    assert summary["result"]["video_resource"].endswith("final_video.mp4")
