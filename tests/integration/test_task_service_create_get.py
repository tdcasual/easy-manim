from video_agent.application.task_service import TaskService
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.strategy_models import StrategyProfile



def test_create_task_returns_poll_metadata(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    SQLiteBootstrapper(temp_settings.database_path).bootstrap()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)

    result = service.create_video_task(prompt="draw a circle", idempotency_key="k1")
    assert result.task_id
    assert result.status == "queued"
    assert result.poll_after_ms == 2000



def test_get_task_returns_snapshot(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    SQLiteBootstrapper(temp_settings.database_path).bootstrap()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)

    created = service.create_video_task(prompt="draw a circle", idempotency_key="k2")
    snapshot = service.get_video_task(created.task_id)
    assert snapshot.task_id == created.task_id
    assert snapshot.phase == "queued"


def test_create_task_applies_global_active_strategy_profile(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    SQLiteBootstrapper(temp_settings.database_path).bootstrap()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)
    strategy = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-global",
            scope="global",
            prompt_cluster=None,
            status="active",
            params={
                "style_hints": {"tone": "teaching"},
                "output_profile": {"quality_preset": "production"},
            },
        )
    )

    created = service.create_video_task(prompt="draw a circle", idempotency_key="global-strategy")
    stored = store.get_task(created.task_id)

    assert stored is not None
    assert stored.strategy_profile_id == strategy.strategy_id
    assert stored.style_hints["tone"] == "teaching"
    assert stored.output_profile["quality_preset"] == "production"


def test_create_task_keeps_explicit_request_overrides_over_active_strategy(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    SQLiteBootstrapper(temp_settings.database_path).bootstrap()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)
    strategy = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-global",
            scope="global",
            prompt_cluster=None,
            status="active",
            params={"style_hints": {"tone": "teaching", "pace": "steady"}},
        )
    )

    created = service.create_video_task(
        prompt="draw a circle",
        idempotency_key="global-strategy-override",
        style_hints={"tone": "dramatic"},
    )
    stored = store.get_task(created.task_id)

    assert stored is not None
    assert stored.strategy_profile_id == strategy.strategy_id
    assert stored.style_hints["tone"] == "dramatic"
    assert stored.style_hints["pace"] == "steady"


def test_create_task_auto_routes_to_cluster_strategy_from_prompt_keywords(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    SQLiteBootstrapper(temp_settings.database_path).bootstrap()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)
    global_strategy = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-global",
            scope="global",
            prompt_cluster=None,
            status="active",
            params={"style_hints": {"tone": "patient"}},
        )
    )
    cluster_strategy = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-geometry",
            scope="global",
            prompt_cluster="geometry",
            status="active",
            params={
                "routing": {"keywords": ["triangle", "geometry"]},
                "style_hints": {"tone": "teaching"},
            },
        )
    )

    created = service.create_video_task(prompt="Explain triangle area proof", idempotency_key="auto-cluster-route")
    stored = store.get_task(created.task_id)

    assert stored is not None
    assert stored.strategy_profile_id == cluster_strategy.strategy_id
    assert stored.strategy_profile_id != global_strategy.strategy_id
    assert stored.style_hints["tone"] == "teaching"


def test_create_task_falls_back_to_global_strategy_when_no_cluster_keyword_matches(temp_settings) -> None:
    store = SQLiteTaskStore(temp_settings.database_path)
    SQLiteBootstrapper(temp_settings.database_path).bootstrap()
    service = TaskService(store=store, artifact_store=ArtifactStore(temp_settings.artifact_root), settings=temp_settings)
    global_strategy = store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-global",
            scope="global",
            prompt_cluster=None,
            status="active",
            params={"style_hints": {"tone": "patient"}},
        )
    )
    store.create_strategy_profile(
        StrategyProfile(
            strategy_id="strategy-geometry",
            scope="global",
            prompt_cluster="geometry",
            status="active",
            params={
                "routing": {"keywords": ["triangle", "geometry"]},
                "style_hints": {"tone": "teaching"},
            },
        )
    )

    created = service.create_video_task(prompt="Draw a circle", idempotency_key="auto-cluster-fallback")
    stored = store.get_task(created.task_id)

    assert stored is not None
    assert stored.strategy_profile_id == global_strategy.strategy_id
    assert stored.style_hints["tone"] == "patient"
