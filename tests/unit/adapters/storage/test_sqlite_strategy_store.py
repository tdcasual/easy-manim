import importlib
import importlib.util
import sqlite3
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.domain.strategy_models import StrategyProfile


MODULE_NAME = "video_agent.adapters.storage.sqlite_strategy_store"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def _build_store(tmp_path: Path):
    module = _load_module()
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    class TestStore(module.SQLiteStrategyStoreMixin):
        STRATEGY_DECISION_TIMELINE_LIMIT = 5

        def __init__(self, database_path: Path) -> None:
            self.database_path = database_path

        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            return connection

    return TestStore(database_path)


def test_strategy_store_mixin_round_trips_profiles_and_filters_active_scope(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    active = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-active",
            scope="global",
            prompt_cluster="beta",
            status="active",
            params={"style_hints": {"tone": "patient"}},
        )
    )
    candidate = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-candidate",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
            params={"style_hints": {"tone": "teaching"}},
        )
    )

    loaded = store.get_strategy_profile(active.strategy_id)
    active_profiles = store.list_strategy_profiles(status="active")
    resolved = store.get_active_strategy_profile(scope="global", prompt_cluster="beta")

    assert loaded is not None
    assert loaded.params["style_hints"]["tone"] == "patient"
    assert [profile.strategy_id for profile in active_profiles] == ["strategy-active"]
    assert resolved is not None
    assert resolved.strategy_id == "strategy-active"
    updated_candidate = store.create_strategy_profile(candidate.model_copy(update={"params": {"version": 2}}))
    assert updated_candidate.created_at == candidate.created_at


def test_strategy_store_mixin_activates_candidate_and_supersedes_previous(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    previous = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-prev",
            scope="global",
            prompt_cluster="beta",
            status="active",
        )
    )
    candidate = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-next",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
        )
    )

    activated, superseded = store.activate_strategy_profile(candidate.strategy_id, applied_at="2026-04-05T00:00:00+00:00")

    assert activated.status == "active"
    assert superseded is not None
    assert superseded.strategy_id == previous.strategy_id
    reloaded_candidate = store.get_strategy_profile(candidate.strategy_id)
    reloaded_previous = store.get_strategy_profile(previous.strategy_id)
    assert reloaded_candidate is not None
    assert reloaded_candidate.metrics["guarded_rollout"]["rollback_target_strategy_id"] == previous.strategy_id
    assert reloaded_candidate.metrics["guarded_rollout"]["rollback_armed"] is True
    assert reloaded_previous is not None
    assert reloaded_previous.status == "superseded"
    assert reloaded_previous.metrics["guarded_rollout"]["superseded_by_strategy_id"] == candidate.strategy_id


def test_strategy_store_mixin_rolls_back_to_previous_strategy(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    previous = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-prev",
            scope="global",
            prompt_cluster="beta",
            status="active",
        )
    )
    candidate = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-next",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
        )
    )
    store.activate_strategy_profile(candidate.strategy_id, applied_at="2026-04-05T00:00:00+00:00")

    rolled_back, restored = store.rollback_strategy_profile(
        candidate.strategy_id,
        rolled_back_at="2026-04-05T01:00:00+00:00",
    )

    assert rolled_back.status == "rolled_back"
    assert restored.strategy_id == previous.strategy_id
    reloaded_candidate = store.get_strategy_profile(candidate.strategy_id)
    reloaded_previous = store.get_strategy_profile(previous.strategy_id)
    assert reloaded_candidate is not None
    assert reloaded_candidate.metrics["guarded_rollout"]["rollback_armed"] is False
    assert reloaded_candidate.metrics["guarded_rollout"]["last_rolled_back_at"] == "2026-04-05T01:00:00+00:00"
    assert reloaded_previous is not None
    assert reloaded_previous.status == "active"
    assert reloaded_previous.metrics["guarded_rollout"]["restored_from_strategy_id"] == candidate.strategy_id


def test_strategy_store_mixin_records_capped_eval_timeline_newest_first(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    profile = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-1",
            scope="global",
            prompt_cluster="beta",
            status="candidate",
        )
    )

    for index in range(7):
        profile = store.record_strategy_eval_run(
            profile.strategy_id,
            baseline_summary={"run_id": f"baseline-{index}", "report": {"success_rate": 0.4, "quality": {"pass_rate": 0.5}}},
            challenger_summary={
                "run_id": f"challenger-{index}",
                "report": {"success_rate": 0.6, "quality": {"pass_rate": 0.7}},
            },
            promotion_recommended=index % 2 == 0,
            promotion_decision={
                "mode": "shadow",
                "applied": False,
                "recorded_at": f"2026-04-05T0{index}:00:00+00:00",
            },
        )

    loaded = store.get_strategy_profile(profile.strategy_id)

    assert loaded is not None
    assert loaded.metrics["last_eval_run"]["challenger_run_id"] == "challenger-6"
    assert loaded.metrics["guarded_rollout"]["consecutive_shadow_passes"] == 1
    timeline = loaded.metrics["decision_timeline"]
    assert len(timeline) == 5
    assert [item["challenger_run_id"] for item in timeline] == [
        "challenger-6",
        "challenger-5",
        "challenger-4",
        "challenger-3",
        "challenger-2",
    ]
