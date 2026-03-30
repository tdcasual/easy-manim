from __future__ import annotations

import argparse
import os
from pathlib import Path

from video_agent.agent_policy import DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError
from video_agent.config import CAPABILITY_ROLLOUT_PROFILES, DEFAULT_STUB_LLM_MODEL, Settings
from video_agent.version import get_release_metadata



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the easy-manim MCP server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-embedded-worker", action="store_true")
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim {metadata['version']} ({metadata['channel']})")
    return parser



def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}



def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_optional_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return int(value)



def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _env_csv(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _render_environment() -> dict[str, str]:
    keys = (
        "TEXMFCNF",
        "TEXMFROOT",
        "TEXMFDIST",
        "TEXMFMAIN",
        "TEXMFSYSVAR",
        "TEXMFSYSCONFIG",
        "TEXMFVAR",
        "TEXMFCONFIG",
    )
    return {key: value for key in keys if (value := os.getenv(key))}


def _env_path(name: str) -> Path | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return Path(value)



def build_settings(data_dir: Path, run_embedded_worker: bool = True) -> Settings:
    rollout_profile = os.getenv("EASY_MANIM_CAPABILITY_ROLLOUT_PROFILE", "supervised")
    normalized_rollout_profile = rollout_profile.strip().lower()
    if normalized_rollout_profile not in CAPABILITY_ROLLOUT_PROFILES:
        supported = ", ".join(sorted(CAPABILITY_ROLLOUT_PROFILES))
        raise ValueError(f"Unsupported capability rollout profile '{rollout_profile}'. Expected one of: {supported}")
    profile_defaults = CAPABILITY_ROLLOUT_PROFILES[normalized_rollout_profile]
    multi_agent_workflow_enabled = _env_bool(
        "EASY_MANIM_MULTI_AGENT_WORKFLOW_ENABLED",
        profile_defaults["multi_agent_workflow_enabled"],
    )
    auto_challenger_env = os.getenv("EASY_MANIM_MULTI_AGENT_WORKFLOW_AUTO_CHALLENGER_ENABLED")
    multi_agent_workflow_auto_challenger_enabled = _env_bool(
        "EASY_MANIM_MULTI_AGENT_WORKFLOW_AUTO_CHALLENGER_ENABLED",
        profile_defaults["multi_agent_workflow_auto_challenger_enabled"],
    )
    if auto_challenger_env is None and not multi_agent_workflow_enabled:
        multi_agent_workflow_auto_challenger_enabled = False
    auto_arbitration_env = os.getenv("EASY_MANIM_MULTI_AGENT_WORKFLOW_AUTO_ARBITRATION_ENABLED")
    multi_agent_workflow_auto_arbitration_enabled = _env_bool(
        "EASY_MANIM_MULTI_AGENT_WORKFLOW_AUTO_ARBITRATION_ENABLED",
        profile_defaults["multi_agent_workflow_auto_arbitration_enabled"],
    )
    if auto_arbitration_env is None and not multi_agent_workflow_enabled:
        multi_agent_workflow_auto_arbitration_enabled = False
    guarded_rollout_env = os.getenv("EASY_MANIM_MULTI_AGENT_WORKFLOW_GUARDED_ROLLOUT_ENABLED")
    multi_agent_workflow_guarded_rollout_enabled = _env_bool(
        "EASY_MANIM_MULTI_AGENT_WORKFLOW_GUARDED_ROLLOUT_ENABLED",
        profile_defaults["multi_agent_workflow_guarded_rollout_enabled"],
    )
    if guarded_rollout_env is None and not multi_agent_workflow_enabled:
        multi_agent_workflow_guarded_rollout_enabled = False
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        eval_root=Path(os.getenv("EASY_MANIM_EVAL_ROOT", str(data_dir / "evals"))),
        auth_mode=os.getenv("EASY_MANIM_AUTH_MODE", "disabled"),
        anonymous_agent_id=os.getenv("EASY_MANIM_ANONYMOUS_AGENT_ID", "local-anonymous"),
        manim_command=os.getenv("EASY_MANIM_MANIM_COMMAND", "manim"),
        latex_command=os.getenv("EASY_MANIM_LATEX_COMMAND", "latex"),
        dvisvgm_command=os.getenv("EASY_MANIM_DVISVGM_COMMAND", "dvisvgm"),
        ffmpeg_command=os.getenv("EASY_MANIM_FFMPEG_COMMAND", "ffmpeg"),
        ffprobe_command=os.getenv("EASY_MANIM_FFPROBE_COMMAND", "ffprobe"),
        render_environment=_render_environment(),
        render_timeout_seconds=_env_int("EASY_MANIM_RENDER_TIMEOUT_SECONDS", 300),
        default_quality_preset=os.getenv("EASY_MANIM_DEFAULT_QUALITY_PRESET", "development"),
        default_frame_rate=_env_optional_int("EASY_MANIM_DEFAULT_FRAME_RATE"),
        default_pixel_width=_env_optional_int("EASY_MANIM_DEFAULT_PIXEL_WIDTH"),
        default_pixel_height=_env_optional_int("EASY_MANIM_DEFAULT_PIXEL_HEIGHT"),
        sandbox_network_disabled=_env_bool("EASY_MANIM_SANDBOX_NETWORK_DISABLED", False),
        sandbox_process_limit=_env_optional_int("EASY_MANIM_SANDBOX_PROCESS_LIMIT"),
        sandbox_memory_limit_mb=_env_optional_int("EASY_MANIM_SANDBOX_MEMORY_LIMIT_MB"),
        sandbox_temp_root=_env_path("EASY_MANIM_SANDBOX_TEMP_ROOT"),
        release_channel=os.getenv("EASY_MANIM_RELEASE_CHANNEL", "beta"),
        default_poll_after_ms=_env_int("EASY_MANIM_DEFAULT_POLL_AFTER_MS", 2000),
        llm_provider=os.getenv("EASY_MANIM_LLM_PROVIDER", "stub"),
        llm_model=os.getenv("EASY_MANIM_LLM_MODEL", DEFAULT_STUB_LLM_MODEL),
        llm_api_base=os.getenv("EASY_MANIM_LLM_API_BASE"),
        llm_api_key=os.getenv("EASY_MANIM_LLM_API_KEY"),
        llm_timeout_seconds=_env_int("EASY_MANIM_LLM_TIMEOUT_SECONDS", 60),
        llm_max_retries=_env_int("EASY_MANIM_LLM_MAX_RETRIES", 2),
        run_embedded_worker=run_embedded_worker,
        worker_poll_interval_seconds=_env_float("EASY_MANIM_WORKER_POLL_INTERVAL_SECONDS", 0.2),
        worker_id=os.getenv("EASY_MANIM_WORKER_ID", "worker-1"),
        worker_lease_seconds=_env_int("EASY_MANIM_WORKER_LEASE_SECONDS", 30),
        worker_recovery_grace_seconds=_env_int("EASY_MANIM_WORKER_RECOVERY_GRACE_SECONDS", 5),
        worker_stale_after_seconds=_env_int("EASY_MANIM_WORKER_STALE_AFTER_SECONDS", 30),
        max_queued_tasks=_env_int("EASY_MANIM_MAX_QUEUED_TASKS", 20),
        max_attempts_per_root_task=_env_int("EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK", 5),
        capability_rollout_profile=rollout_profile,
        agent_learning_auto_apply_enabled=_env_bool(
            "EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_ENABLED",
            profile_defaults["agent_learning_auto_apply_enabled"],
        ),
        agent_learning_auto_apply_min_completed_tasks=_env_int("EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_MIN_COMPLETED_TASKS", 5),
        agent_learning_auto_apply_min_quality_score=_env_float("EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_MIN_QUALITY_SCORE", 0.9),
        agent_learning_auto_apply_max_recent_failures=_env_int("EASY_MANIM_AGENT_LEARNING_AUTO_APPLY_MAX_RECENT_FAILURES", 0),
        auto_repair_enabled=_env_bool(
            "EASY_MANIM_AUTO_REPAIR_ENABLED",
            profile_defaults["auto_repair_enabled"],
        ),
        delivery_guarantee_enabled=_env_bool(
            "EASY_MANIM_DELIVERY_GUARANTEE_ENABLED",
            profile_defaults["delivery_guarantee_enabled"],
        ),
        auto_repair_max_children_per_root=_env_int("EASY_MANIM_AUTO_REPAIR_MAX_CHILDREN_PER_ROOT", 2),
        auto_repair_retryable_issue_codes=_env_csv(
            "EASY_MANIM_AUTO_REPAIR_RETRYABLE_ISSUE_CODES",
            DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES,
        ),
        multi_agent_workflow_enabled=multi_agent_workflow_enabled,
        multi_agent_workflow_auto_challenger_enabled=multi_agent_workflow_auto_challenger_enabled,
        multi_agent_workflow_auto_arbitration_enabled=multi_agent_workflow_auto_arbitration_enabled,
        multi_agent_workflow_guarded_rollout_enabled=multi_agent_workflow_guarded_rollout_enabled,
        multi_agent_workflow_guarded_min_delivery_rate=_env_float(
            "EASY_MANIM_MULTI_AGENT_WORKFLOW_GUARDED_MIN_DELIVERY_RATE",
            0.9,
        ),
        multi_agent_workflow_guarded_max_emergency_fallback_rate=_env_float(
            "EASY_MANIM_MULTI_AGENT_WORKFLOW_GUARDED_MAX_EMERGENCY_FALLBACK_RATE",
            0.10,
        ),
        multi_agent_workflow_guarded_max_branch_rejection_rate=_env_float(
            "EASY_MANIM_MULTI_AGENT_WORKFLOW_GUARDED_MAX_BRANCH_REJECTION_RATE",
            0.50,
        ),
        multi_agent_workflow_max_child_attempts=_env_int("EASY_MANIM_MULTI_AGENT_WORKFLOW_MAX_CHILD_ATTEMPTS", 3),
        multi_agent_workflow_require_completed_for_accept=_env_bool(
            "EASY_MANIM_MULTI_AGENT_WORKFLOW_REQUIRE_COMPLETED_FOR_ACCEPT",
            True,
        ),
        preview_gate_enabled=_env_bool("EASY_MANIM_PREVIEW_GATE_ENABLED", True),
        preview_gate_frame_limit=_env_int("EASY_MANIM_PREVIEW_GATE_FRAME_LIMIT", 12),
        quality_gate_min_score=_env_float("EASY_MANIM_QUALITY_GATE_MIN_SCORE", 0.75),
        risk_routing_enabled=_env_bool("EASY_MANIM_RISK_ROUTING_ENABLED", True),
        strategy_promotion_enabled=_env_bool(
            "EASY_MANIM_STRATEGY_PROMOTION_ENABLED",
            profile_defaults["strategy_promotion_enabled"],
        ),
        strategy_promotion_guarded_auto_apply_enabled=_env_bool(
            "EASY_MANIM_STRATEGY_PROMOTION_GUARDED_AUTO_APPLY_ENABLED",
            profile_defaults["strategy_promotion_guarded_auto_apply_enabled"],
        ),
        strategy_promotion_guarded_auto_apply_min_shadow_passes=_env_int(
            "EASY_MANIM_STRATEGY_PROMOTION_GUARDED_AUTO_APPLY_MIN_SHADOW_PASSES",
            3,
        ),
        strategy_promotion_guarded_auto_rollback_enabled=_env_bool(
            "EASY_MANIM_STRATEGY_PROMOTION_GUARDED_AUTO_ROLLBACK_ENABLED",
            True,
        ),
    )



def main() -> None:
    from video_agent.server.fastmcp_server import create_mcp_server

    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir, run_embedded_worker=not args.no_embedded_worker)
    try:
        mcp = create_mcp_server(settings, host=args.host, port=args.port, debug=args.debug)
    except DatabaseBootstrapRequiredError as exc:
        raise SystemExit(str(exc)) from exc
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
