from pathlib import Path

import pytest

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (
            "conservative",
            {
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
        ),
        (
            "supervised",
            {
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
        ),
        (
            "autonomy-lite",
            {
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
        ),
        (
            "autonomy-guarded",
            {
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
        ),
    ],
)
def test_runtime_status_reports_capability_rollout_profile(
    tmp_path: Path,
    profile: str,
    expected: dict[str, bool],
) -> None:
    data_dir = tmp_path / profile
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        capability_rollout_profile=profile,
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["capabilities"]["rollout_profile"] == profile
    assert payload["capabilities"]["effective"] == expected


def test_capability_rollout_profile_preserves_explicit_settings_override(tmp_path: Path) -> None:
    data_dir = tmp_path / "override"
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        capability_rollout_profile="autonomy-lite",
        strategy_promotion_enabled=False,
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["capabilities"]["rollout_profile"] == "autonomy-lite"
    assert payload["capabilities"]["effective"]["agent_learning_auto_apply_enabled"] is True
    assert payload["capabilities"]["effective"]["auto_repair_enabled"] is True
    assert payload["capabilities"]["effective"]["delivery_guarantee_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_auto_challenger_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_auto_arbitration_enabled"] is True
    assert payload["capabilities"]["effective"]["multi_agent_workflow_guarded_rollout_enabled"] is False
    assert payload["capabilities"]["effective"]["strategy_promotion_enabled"] is False
    assert payload["capabilities"]["effective"]["strategy_promotion_guarded_auto_apply_enabled"] is True
