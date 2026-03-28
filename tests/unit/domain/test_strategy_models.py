from video_agent.domain.strategy_models import PromptClusterStats, StrategyProfile


def test_strategy_profile_tracks_scope_and_metrics() -> None:
    profile = StrategyProfile(
        strategy_id="strategy-1",
        scope="global",
        status="draft",
        params={"generation_mode": "template_first"},
        metrics={"success_rate": 0.75},
    )

    assert profile.scope == "global"
    assert profile.params["generation_mode"] == "template_first"
    assert profile.metrics["success_rate"] == 0.75


def test_prompt_cluster_stats_tracks_success_rate() -> None:
    stats = PromptClusterStats(
        prompt_cluster="geometry",
        total_runs=12,
        success_rate=0.5,
    )

    assert stats.prompt_cluster == "geometry"
    assert stats.total_runs == 12
    assert stats.success_rate == 0.5
