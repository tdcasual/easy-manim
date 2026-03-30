from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator
from video_agent.agent_policy import DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES

DEFAULT_STUB_LLM_MODEL = "stub-manim-v1"
CAPABILITY_ROLLOUT_PROFILES: dict[str, dict[str, bool]] = {
    "conservative": {
        "agent_learning_auto_apply_enabled": False,
        "auto_repair_enabled": False,
        "delivery_guarantee_enabled": False,
        "multi_agent_workflow_enabled": False,
        "multi_agent_workflow_auto_challenger_enabled": False,
        "multi_agent_workflow_auto_arbitration_enabled": False,
        "multi_agent_workflow_guarded_rollout_enabled": False,
        "strategy_promotion_enabled": False,
        "strategy_promotion_guarded_auto_apply_enabled": False,
    },
    "supervised": {
        "agent_learning_auto_apply_enabled": False,
        "auto_repair_enabled": True,
        "delivery_guarantee_enabled": True,
        "multi_agent_workflow_enabled": True,
        "multi_agent_workflow_auto_challenger_enabled": True,
        "multi_agent_workflow_auto_arbitration_enabled": True,
        "multi_agent_workflow_guarded_rollout_enabled": False,
        "strategy_promotion_enabled": False,
        "strategy_promotion_guarded_auto_apply_enabled": False,
    },
    "autonomy-lite": {
        "agent_learning_auto_apply_enabled": True,
        "auto_repair_enabled": True,
        "delivery_guarantee_enabled": True,
        "multi_agent_workflow_enabled": True,
        "multi_agent_workflow_auto_challenger_enabled": True,
        "multi_agent_workflow_auto_arbitration_enabled": True,
        "multi_agent_workflow_guarded_rollout_enabled": False,
        "strategy_promotion_enabled": True,
        "strategy_promotion_guarded_auto_apply_enabled": True,
    },
    "autonomy-guarded": {
        "agent_learning_auto_apply_enabled": True,
        "auto_repair_enabled": True,
        "delivery_guarantee_enabled": True,
        "multi_agent_workflow_enabled": True,
        "multi_agent_workflow_auto_challenger_enabled": True,
        "multi_agent_workflow_auto_arbitration_enabled": True,
        "multi_agent_workflow_guarded_rollout_enabled": True,
        "strategy_promotion_enabled": True,
        "strategy_promotion_guarded_auto_apply_enabled": True,
    },
}


class Settings(BaseModel):
    data_dir: Path = Path("data")
    database_path: Optional[Path] = None
    artifact_root: Optional[Path] = None
    eval_root: Optional[Path] = None
    auth_mode: str = "disabled"
    anonymous_agent_id: str = "local-anonymous"
    manim_command: str = "manim"
    latex_command: str = "latex"
    dvisvgm_command: str = "dvisvgm"
    ffmpeg_command: str = "ffmpeg"
    ffprobe_command: str = "ffprobe"
    render_environment: dict[str, str] = Field(default_factory=dict)
    render_timeout_seconds: int = 300
    default_quality_preset: str = "development"
    default_frame_rate: int | None = None
    default_pixel_width: int | None = None
    default_pixel_height: int | None = None
    sandbox_network_disabled: bool = False
    sandbox_process_limit: int | None = None
    sandbox_memory_limit_mb: int | None = None
    sandbox_temp_root: Optional[Path] = None
    release_channel: str = "beta"
    default_poll_after_ms: int = 2000
    llm_provider: str = "stub"
    llm_model: str = DEFAULT_STUB_LLM_MODEL
    llm_api_base: Optional[str] = None
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
    session_memory_max_entries: int = 5
    session_memory_max_attempts_per_entry: int = 3
    session_memory_summary_char_limit: int = 2000
    persistent_memory_backend: str = "local"
    persistent_memory_enable_embeddings: bool = False
    persistent_memory_embedding_provider: str | None = None
    persistent_memory_embedding_model: str | None = None
    capability_rollout_profile: str = "supervised"
    agent_learning_auto_apply_enabled: bool = False
    agent_learning_auto_apply_min_completed_tasks: int = 5
    agent_learning_auto_apply_min_quality_score: float = 0.9
    agent_learning_auto_apply_max_recent_failures: int = 0
    auto_repair_enabled: bool = False
    auto_repair_max_children_per_root: int = 2
    auto_repair_retryable_issue_codes: list[str] = Field(
        default_factory=lambda: list(DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES)
    )
    multi_agent_workflow_enabled: bool = False
    multi_agent_workflow_auto_challenger_enabled: bool = False
    multi_agent_workflow_auto_arbitration_enabled: bool = False
    multi_agent_workflow_guarded_rollout_enabled: bool = False
    multi_agent_workflow_guarded_min_delivery_rate: float = 0.9
    multi_agent_workflow_guarded_max_emergency_fallback_rate: float = 0.10
    multi_agent_workflow_guarded_max_branch_rejection_rate: float = 0.50
    multi_agent_workflow_max_child_attempts: int = 3
    multi_agent_workflow_require_completed_for_accept: bool = True
    preview_gate_enabled: bool = True
    preview_gate_frame_limit: int = 12
    quality_gate_min_score: float = 0.75
    risk_routing_enabled: bool = True
    strategy_promotion_enabled: bool = False
    strategy_promotion_guarded_auto_apply_enabled: bool = False
    strategy_promotion_guarded_auto_apply_min_shadow_passes: int = 3
    strategy_promotion_guarded_auto_rollback_enabled: bool = True
    strategy_promotion_max_success_regression: float = 0.0
    strategy_promotion_min_quality_gain: float = 0.01
    strategy_promotion_max_must_fix_issue_rate: float = 0.10
    strategy_promotion_max_repair_rate_regression: float = 0.05
    delivery_guarantee_enabled: bool = False
    delivery_guarantee_allow_emergency_video: bool = True

    @model_validator(mode="after")
    def derive_paths(self) -> "Settings":
        profile_name = self.capability_rollout_profile.strip().lower()
        if profile_name not in CAPABILITY_ROLLOUT_PROFILES:
            supported = ", ".join(sorted(CAPABILITY_ROLLOUT_PROFILES))
            raise ValueError(f"Unsupported capability rollout profile '{self.capability_rollout_profile}'. Expected one of: {supported}")
        self.capability_rollout_profile = profile_name
        for flag_name, enabled in CAPABILITY_ROLLOUT_PROFILES[profile_name].items():
            if flag_name not in self.model_fields_set:
                setattr(self, flag_name, enabled)
        if (
            not self.multi_agent_workflow_enabled
            and "multi_agent_workflow_auto_challenger_enabled" not in self.model_fields_set
        ):
            self.multi_agent_workflow_auto_challenger_enabled = False
        if (
            not self.multi_agent_workflow_enabled
            and "multi_agent_workflow_auto_arbitration_enabled" not in self.model_fields_set
        ):
            self.multi_agent_workflow_auto_arbitration_enabled = False
        if (
            not self.multi_agent_workflow_enabled
            and "multi_agent_workflow_guarded_rollout_enabled" not in self.model_fields_set
        ):
            self.multi_agent_workflow_guarded_rollout_enabled = False
        if self.database_path is None:
            self.database_path = self.data_dir / "video_agent.db"
        if self.artifact_root is None:
            self.artifact_root = self.data_dir / "tasks"
        if self.eval_root is None:
            self.eval_root = self.data_dir / "evals"
        if self.sandbox_temp_root is None:
            self.sandbox_temp_root = self.artifact_root / ".sandbox" / "tmp"
        if self.sandbox_process_limit is not None and self.sandbox_process_limit <= 0:
            self.sandbox_process_limit = None
        if self.sandbox_memory_limit_mb is not None and self.sandbox_memory_limit_mb <= 0:
            self.sandbox_memory_limit_mb = None
        if self.default_frame_rate is not None and self.default_frame_rate <= 0:
            self.default_frame_rate = None
        if self.default_pixel_width is not None and self.default_pixel_width <= 0:
            self.default_pixel_width = None
        if self.default_pixel_height is not None and self.default_pixel_height <= 0:
            self.default_pixel_height = None
        if self.strategy_promotion_guarded_auto_apply_min_shadow_passes <= 0:
            self.strategy_promotion_guarded_auto_apply_min_shadow_passes = 1
        self.multi_agent_workflow_guarded_min_delivery_rate = min(
            max(self.multi_agent_workflow_guarded_min_delivery_rate, 0.0),
            1.0,
        )
        self.multi_agent_workflow_guarded_max_emergency_fallback_rate = min(
            max(self.multi_agent_workflow_guarded_max_emergency_fallback_rate, 0.0),
            1.0,
        )
        self.multi_agent_workflow_guarded_max_branch_rejection_rate = min(
            max(self.multi_agent_workflow_guarded_max_branch_rejection_rate, 0.0),
            1.0,
        )
        return self
