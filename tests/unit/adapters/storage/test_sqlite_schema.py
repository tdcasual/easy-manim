import importlib
import importlib.util
import sqlite3


def _load_module(module_name: str):
    spec = importlib.util.find_spec(module_name)
    assert spec is not None
    return importlib.import_module(module_name)


def test_sqlite_schema_composes_split_migration_packs_and_bootstraps_expected_tables() -> None:
    root = _load_module("video_agent.adapters.storage.sqlite_schema")
    core = _load_module("video_agent.adapters.storage.sqlite_schema_core")
    learning = _load_module("video_agent.adapters.storage.sqlite_schema_learning")
    delivery = _load_module("video_agent.adapters.storage.sqlite_schema_delivery")
    threads = _load_module("video_agent.adapters.storage.sqlite_schema_threads")

    expected_apply_functions = {
        "001_initial_schema": core.apply_initial_schema,
        "002_legacy_shape_reconciliation": core.apply_legacy_shape_reconciliation,
        "003_agent_learning_normalization": learning.apply_agent_learning_normalization,
        "004_agent_session_token_binding": learning.apply_agent_session_token_binding,
        "005_task_display_title_fields": core.apply_task_display_title_fields,
        "006_task_reliability_fields": delivery.apply_task_reliability_fields,
        "007_task_quality_scorecards": delivery.apply_task_quality_scorecards,
        "008_strategy_profiles": learning.apply_strategy_profiles,
        "009_agent_learning_quality_split": learning.apply_agent_learning_quality_split,
        "010_delivery_case_scaffold": delivery.apply_delivery_case_scaffold,
        "011_session_memory_snapshot_scaffold": learning.apply_session_memory_snapshot_scaffold,
        "012_workflow_participant_scaffold": delivery.apply_workflow_participant_scaffold,
        "013_task_event_ordering_indexes": core.apply_task_event_ordering_indexes,
        "014_video_thread_runtime_scaffold": threads.apply_video_thread_runtime_scaffold,
    }

    assert {
        migration.migration_id: migration.apply
        for migration in root.SQLITE_MIGRATIONS
    } == expected_apply_functions

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        for migration in root.SQLITE_MIGRATIONS:
            migration.apply(connection)

        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        indexes = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
        }
    finally:
        connection.close()

    assert {
        "video_tasks",
        "agent_memories",
        "strategy_profiles",
        "delivery_cases",
        "workflow_participants",
        "video_threads",
        "video_iterations",
        "video_thread_participants",
    } <= tables
    assert {
        "idx_agent_learning_events_task_id",
        "idx_delivery_cases_root_task_id",
        "idx_session_memory_snapshots_agent_updated_at",
        "idx_workflow_participants_root_role",
        "idx_task_events_task_id_id",
        "idx_video_iterations_thread_created_at",
    } <= indexes
