from __future__ import annotations

from video_agent.adapters.storage.sqlite_schema_core import (
    MigrationAction,
    SCHEMA_MIGRATIONS_SQL,
    SCHEMA_MIGRATIONS_TABLE,
    SQLiteMigration,
    apply_initial_schema,
    apply_legacy_shape_reconciliation,
    apply_task_memory_context_projection,
    apply_task_display_title_fields,
    apply_task_event_ordering_indexes,
    ensure_column,
    has_table,
)
from video_agent.adapters.storage.sqlite_schema_delivery import (
    apply_delivery_case_scaffold,
    apply_task_quality_scorecards,
    apply_task_reliability_fields,
    apply_workflow_participant_scaffold,
)
from video_agent.adapters.storage.sqlite_schema_learning import (
    apply_agent_learning_normalization,
    apply_agent_learning_quality_split,
    apply_agent_session_token_binding,
    apply_session_memory_snapshot_scaffold,
    apply_strategy_profiles,
)
from video_agent.adapters.storage.sqlite_schema_threads import apply_video_thread_runtime_scaffold
from video_agent.adapters.storage.sqlite_schema_runtime import apply_agent_runtime_definition_scaffold


SQLITE_MIGRATIONS: tuple[SQLiteMigration, ...] = (
    SQLiteMigration(
        migration_id="001_initial_schema",
        description="create the core sqlite schema",
        apply=apply_initial_schema,
    ),
    SQLiteMigration(
        migration_id="002_legacy_shape_reconciliation",
        description="reconcile legacy task and profile columns",
        apply=apply_legacy_shape_reconciliation,
    ),
    SQLiteMigration(
        migration_id="003_agent_learning_normalization",
        description="dedupe learning events and create supporting indexes",
        apply=apply_agent_learning_normalization,
    ),
    SQLiteMigration(
        migration_id="004_agent_session_token_binding",
        description="bind agent sessions to the issuing token hash",
        apply=apply_agent_session_token_binding,
    ),
    SQLiteMigration(
        migration_id="005_task_display_title_fields",
        description="persist display titles and sources for tasks",
        apply=apply_task_display_title_fields,
    ),
    SQLiteMigration(
        migration_id="006_task_reliability_fields",
        description="persist reliability metadata for tasks",
        apply=apply_task_reliability_fields,
    ),
    SQLiteMigration(
        migration_id="007_task_quality_scorecards",
        description="create a table for task quality scorecards",
        apply=apply_task_quality_scorecards,
    ),
    SQLiteMigration(
        migration_id="008_strategy_profiles",
        description="create a table for strategy profiles",
        apply=apply_strategy_profiles,
    ),
    SQLiteMigration(
        migration_id="009_agent_learning_quality_split",
        description="persist quality-passed flags for agent learning events",
        apply=apply_agent_learning_quality_split,
    ),
    SQLiteMigration(
        migration_id="010_delivery_case_scaffold",
        description="persist delivery cases and agent runs for native orchestration scaffolding",
        apply=apply_delivery_case_scaffold,
    ),
    SQLiteMigration(
        migration_id="011_session_memory_snapshot_scaffold",
        description="persist session memory snapshots for restart recovery",
        apply=apply_session_memory_snapshot_scaffold,
    ),
    SQLiteMigration(
        migration_id="012_workflow_participant_scaffold",
        description="persist workflow participants for collaboration access control",
        apply=apply_workflow_participant_scaffold,
    ),
    SQLiteMigration(
        migration_id="013_task_event_ordering_indexes",
        description="index task events for ordered discussion thread loading",
        apply=apply_task_event_ordering_indexes,
    ),
    SQLiteMigration(
        migration_id="014_video_thread_runtime_scaffold",
        description="persist video thread runtime entities and task bindings",
        apply=apply_video_thread_runtime_scaffold,
    ),
    SQLiteMigration(
        migration_id="015_agent_runtime_definition_scaffold",
        description="persist openclaw-style agent runtime definitions",
        apply=apply_agent_runtime_definition_scaffold,
    ),
    SQLiteMigration(
        migration_id="016_task_memory_context_projection",
        description="project structured task memory context into dedicated sqlite columns",
        apply=apply_task_memory_context_projection,
    ),
)

__all__ = [
    "MigrationAction",
    "SCHEMA_MIGRATIONS_SQL",
    "SCHEMA_MIGRATIONS_TABLE",
    "SQLITE_MIGRATIONS",
    "SQLiteMigration",
    "ensure_column",
    "has_table",
]
