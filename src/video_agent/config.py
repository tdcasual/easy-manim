from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Settings(BaseModel):
    data_dir: Path = Path("data")
    database_path: Optional[Path] = None
    artifact_root: Optional[Path] = None
    eval_root: Optional[Path] = None
    manim_command: str = "manim"
    latex_command: str = "latex"
    dvisvgm_command: str = "dvisvgm"
    ffmpeg_command: str = "ffmpeg"
    ffprobe_command: str = "ffprobe"
    render_environment: dict[str, str] = Field(default_factory=dict)
    release_channel: str = "beta"
    default_poll_after_ms: int = 2000
    llm_provider: str = "stub"
    llm_model: str = "stub-manim-v1"
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    run_embedded_worker: bool = True
    worker_poll_interval_seconds: float = 0.2
    worker_id: str = "worker-1"
    worker_lease_seconds: int = 30
    worker_recovery_grace_seconds: int = 5
    worker_stale_after_seconds: int = 30
    max_queued_tasks: int = 20
    max_attempts_per_root_task: int = 5
    auto_repair_enabled: bool = False
    auto_repair_max_children_per_root: int = 1
    auto_repair_retryable_issue_codes: list[str] = Field(
        default_factory=lambda: [
            "render_failed",
            "generation_failed",
            "syntax_error",
            "missing_scene",
            "black_frames",
            "frozen_tail",
            "encoding_error",
            "min_width_not_met",
            "min_height_not_met",
            "min_duration_not_met",
        ]
    )

    @model_validator(mode="after")
    def derive_paths(self) -> "Settings":
        if self.database_path is None:
            self.database_path = self.data_dir / "video_agent.db"
        if self.artifact_root is None:
            self.artifact_root = self.data_dir / "tasks"
        if self.eval_root is None:
            self.eval_root = self.data_dir / "evals"
        return self
