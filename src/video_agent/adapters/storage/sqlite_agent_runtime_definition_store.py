from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from video_agent.domain.agent_runtime_models import AgentRuntimeDefinition
from video_agent.domain.agent_runtime_run_models import AgentRuntimeRun


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SQLiteAgentRuntimeDefinitionStoreMixin:
    def upsert_agent_runtime_definition(
        self,
        definition: AgentRuntimeDefinition,
    ) -> AgentRuntimeDefinition:
        definition.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT created_at
                FROM agent_runtime_definitions
                WHERE agent_id = ?
                """,
                (definition.agent_id,),
            ).fetchone()
            if existing is not None:
                definition.created_at = datetime.fromisoformat(existing["created_at"])
            connection.execute(
                """
                INSERT INTO agent_runtime_definitions (
                    agent_id, name, status, workspace, agent_dir, tools_allow_json,
                    channels_json, delegate_metadata_json, definition_source, runtime_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    workspace = excluded.workspace,
                    agent_dir = excluded.agent_dir,
                    tools_allow_json = excluded.tools_allow_json,
                    channels_json = excluded.channels_json,
                    delegate_metadata_json = excluded.delegate_metadata_json,
                    definition_source = excluded.definition_source,
                    runtime_json = excluded.runtime_json,
                    updated_at = excluded.updated_at
                """,
                (
                    definition.agent_id,
                    definition.name,
                    definition.status,
                    definition.workspace,
                    definition.agent_dir,
                    json.dumps(definition.tools_allow),
                    json.dumps(definition.channels),
                    json.dumps(definition.delegate_metadata),
                    definition.definition_source,
                    definition.model_dump_json(),
                    definition.created_at.isoformat(),
                    definition.updated_at.isoformat(),
                ),
            )
        return definition

    def get_agent_runtime_definition(self, agent_id: str) -> AgentRuntimeDefinition | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT runtime_json
                FROM agent_runtime_definitions
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return AgentRuntimeDefinition.model_validate_json(row["runtime_json"])

    def create_agent_runtime_run(self, run: AgentRuntimeRun) -> AgentRuntimeRun:
        run.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runtime_runs (
                    run_id, session_id, agent_id, source_kind, trigger_kind, status,
                    task_id, thread_id, iteration_id, summary, run_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.session_id,
                    run.agent_id,
                    run.source_kind,
                    run.trigger_kind,
                    run.status,
                    run.task_id,
                    run.thread_id,
                    run.iteration_id,
                    run.summary,
                    run.model_dump_json(),
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
        return run

    def list_agent_runtime_runs(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[AgentRuntimeRun]:
        query = "SELECT run_json FROM agent_runtime_runs WHERE 1 = 1"
        params: list[object] = []
        if session_id is not None:
            query += " AND session_id = ?"
            params.append(session_id)
        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY created_at ASC, run_id ASC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [AgentRuntimeRun.model_validate_json(row["run_json"]) for row in rows]
