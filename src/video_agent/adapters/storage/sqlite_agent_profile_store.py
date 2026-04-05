from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from video_agent.application.preference_resolver import resolve_effective_request_config
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.agent_profile_revision_models import AgentProfileRevision
from video_agent.domain.agent_profile_suggestion_models import AgentProfileSuggestion


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


class SQLiteAgentProfileStoreMixin:
    def upsert_agent_profile(self, profile: AgentProfile) -> None:
        profile.updated_at = _utcnow()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT name, status, profile_version, profile_json, policy_json, created_at, updated_at
                FROM agent_profiles
                WHERE agent_id = ?
                """,
                (profile.agent_id,),
            ).fetchone()
            profile_version = profile.profile_version
            created_at = profile.created_at
            if existing is not None:
                profile_changed = (
                    existing["name"] != profile.name
                    or existing["status"] != profile.status
                    or json.loads(existing["profile_json"]) != profile.profile_json
                    or json.loads(existing["policy_json"]) != profile.policy_json
                )
                profile_version = int(existing["profile_version"]) + 1 if profile_changed else int(existing["profile_version"])
                created_at = datetime.fromisoformat(existing["created_at"])
            profile.profile_version = profile_version
            profile.created_at = created_at
            connection.execute(
                """
                INSERT INTO agent_profiles (
                    agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    name = excluded.name,
                    status = excluded.status,
                    profile_version = excluded.profile_version,
                    profile_json = excluded.profile_json,
                    policy_json = excluded.policy_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.agent_id,
                    profile.name,
                    profile.status,
                    profile.profile_version,
                    json.dumps(profile.profile_json),
                    json.dumps(profile.policy_json),
                    profile.created_at.isoformat(),
                    profile.updated_at.isoformat(),
                ),
            )

    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at
                FROM agent_profiles
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_profile(row)

    def apply_agent_profile_patch(
        self,
        agent_id: str,
        *,
        patch_json: dict[str, Any],
        source: str,
    ) -> tuple[AgentProfile, AgentProfileRevision]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated_profile, revision = self._apply_agent_profile_patch_in_connection(
                connection,
                agent_id=agent_id,
                patch_json=patch_json,
                source=source,
            )
            connection.commit()
        return updated_profile, revision

    def apply_agent_profile_suggestion(
        self,
        agent_id: str,
        *,
        suggestion_id: str,
        source: str,
    ) -> tuple[AgentProfile, AgentProfileRevision, AgentProfileSuggestion]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            suggestion_row = connection.execute(
                """
                SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                FROM agent_profile_suggestions
                WHERE suggestion_id = ?
                """,
                (suggestion_id,),
            ).fetchone()
            if suggestion_row is None:
                raise ValueError("profile suggestion not found")

            suggestion = self._row_to_agent_profile_suggestion(suggestion_row)
            if suggestion.agent_id != agent_id:
                raise PermissionError("agent_access_denied")
            if suggestion.status != "pending":
                raise RuntimeError("profile_suggestion_state_conflict")

            updated_profile, revision = self._apply_agent_profile_patch_in_connection(
                connection,
                agent_id=agent_id,
                patch_json=suggestion.patch_json,
                source=source,
            )
            result = connection.execute(
                """
                UPDATE agent_profile_suggestions
                SET status = ?, applied_at = COALESCE(applied_at, ?)
                WHERE suggestion_id = ? AND status = ?
                """,
                (
                    "applied",
                    updated_profile.updated_at.isoformat(),
                    suggestion_id,
                    "pending",
                ),
            )
            if result.rowcount == 0:
                raise RuntimeError("profile_suggestion_state_conflict")

            connection.commit()
        return (
            updated_profile,
            revision,
            suggestion.model_copy(
                update={
                    "status": "applied",
                    "applied_at": suggestion.applied_at or updated_profile.updated_at,
                }
            ),
        )

    def create_agent_profile_revision(self, revision: AgentProfileRevision) -> AgentProfileRevision:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_profile_revisions (
                    revision_id, agent_id, patch_json, source, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.agent_id,
                    json.dumps(revision.patch_json),
                    revision.source,
                    revision.created_at.isoformat(),
                ),
            )
        return revision

    def create_agent_learning_event(self, event: AgentLearningEvent) -> AgentLearningEvent:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_learning_events (
                    event_id, agent_id, task_id, session_id, status, quality_passed, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    session_id = excluded.session_id,
                    status = excluded.status,
                    quality_passed = excluded.quality_passed,
                    issue_codes_json = excluded.issue_codes_json,
                    quality_score = excluded.quality_score,
                    profile_digest = excluded.profile_digest,
                    memory_ids_json = excluded.memory_ids_json
                """,
                (
                    event.event_id,
                    event.agent_id,
                    event.task_id,
                    event.session_id,
                    event.status,
                    None if event.quality_passed is None else int(event.quality_passed),
                    json.dumps(event.issue_codes),
                    event.quality_score,
                    event.profile_digest,
                    json.dumps(event.memory_ids),
                    event.created_at.isoformat(),
                ),
            )
            row = connection.execute(
                """
                SELECT
                    event_id, agent_id, task_id, session_id, status, quality_passed, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                FROM agent_learning_events
                WHERE task_id = ?
                """,
                (event.task_id,),
            ).fetchone()
        if row is None:
            return event
        return self._row_to_agent_learning_event(row)

    def list_agent_learning_events(self, agent_id: str, limit: int = 200) -> list[AgentLearningEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id, agent_id, task_id, session_id, status, quality_passed, issue_codes_json,
                    quality_score, profile_digest, memory_ids_json, created_at
                FROM agent_learning_events
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [self._row_to_agent_learning_event(row) for row in rows]

    def create_agent_profile_suggestion(self, suggestion: AgentProfileSuggestion) -> AgentProfileSuggestion:
        patch_json = _canonical_json(suggestion.patch_json)
        rationale_json = _canonical_json(suggestion.rationale_json)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if suggestion.status == "pending":
                pending_rows = connection.execute(
                    """
                    SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                    FROM agent_profile_suggestions
                    WHERE agent_id = ? AND status = ?
                    ORDER BY created_at DESC
                    """,
                    (suggestion.agent_id, "pending"),
                ).fetchall()
                for row in pending_rows:
                    if (
                        _canonical_json(json.loads(row["patch_json"])) == patch_json
                        and _canonical_json(json.loads(row["rationale_json"])) == rationale_json
                    ):
                        return self._row_to_agent_profile_suggestion(row)

            connection.execute(
                """
                INSERT INTO agent_profile_suggestions (
                    suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    suggestion.suggestion_id,
                    suggestion.agent_id,
                    patch_json,
                    rationale_json,
                    suggestion.status,
                    suggestion.created_at.isoformat(),
                    None if suggestion.applied_at is None else suggestion.applied_at.isoformat(),
                ),
            )
            connection.commit()
        return suggestion

    def get_agent_profile_suggestion(self, suggestion_id: str) -> Optional[AgentProfileSuggestion]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                FROM agent_profile_suggestions
                WHERE suggestion_id = ?
                """,
                (suggestion_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_profile_suggestion(row)

    def list_agent_profile_suggestions(self, agent_id: str, limit: int = 50) -> list[AgentProfileSuggestion]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT suggestion_id, agent_id, patch_json, rationale_json, status, created_at, applied_at
                FROM agent_profile_suggestions
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [self._row_to_agent_profile_suggestion(row) for row in rows]

    def update_agent_profile_suggestion_status(
        self,
        suggestion_id: str,
        *,
        status: str,
        applied_at: datetime | None = None,
        expected_status: str | None = None,
    ) -> Optional[AgentProfileSuggestion]:
        with self._connect() as connection:
            if expected_status is None:
                result = connection.execute(
                    """
                    UPDATE agent_profile_suggestions
                    SET status = ?, applied_at = COALESCE(applied_at, ?)
                    WHERE suggestion_id = ?
                    """,
                    (
                        status,
                        None if applied_at is None else applied_at.isoformat(),
                        suggestion_id,
                    ),
                )
            else:
                result = connection.execute(
                    """
                    UPDATE agent_profile_suggestions
                    SET status = ?, applied_at = COALESCE(applied_at, ?)
                    WHERE suggestion_id = ? AND status = ?
                    """,
                    (
                        status,
                        None if applied_at is None else applied_at.isoformat(),
                        suggestion_id,
                        expected_status,
                    ),
                )
        if result.rowcount == 0:
            return None
        return self.get_agent_profile_suggestion(suggestion_id)

    def list_agent_profile_revisions(self, agent_id: str, limit: int = 50) -> list[AgentProfileRevision]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT revision_id, agent_id, patch_json, source, created_at
                FROM agent_profile_revisions
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        return [
            AgentProfileRevision(
                revision_id=row["revision_id"],
                agent_id=row["agent_id"],
                patch_json=json.loads(row["patch_json"]),
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def _apply_agent_profile_patch_in_connection(
        self,
        connection: sqlite3.Connection,
        *,
        agent_id: str,
        patch_json: dict[str, Any],
        source: str,
    ) -> tuple[AgentProfile, AgentProfileRevision]:
        row = connection.execute(
            """
            SELECT agent_id, name, status, profile_version, profile_json, policy_json, created_at, updated_at
            FROM agent_profiles
            WHERE agent_id = ?
            """,
            (agent_id,),
        ).fetchone()
        if row is None:
            raise ValueError("agent profile not found")

        current_profile = self._row_to_agent_profile(row)
        if current_profile.status != "active":
            raise ValueError("inactive agent profile")
        updated_profile_json = resolve_effective_request_config(
            profile_json=current_profile.profile_json,
            request_overrides=patch_json,
        )
        updated_profile = current_profile.model_copy(
            update={
                "profile_json": updated_profile_json,
                "profile_version": (
                    current_profile.profile_version + 1
                    if updated_profile_json != current_profile.profile_json
                    else current_profile.profile_version
                ),
                "updated_at": _utcnow(),
            }
        )
        connection.execute(
            """
            UPDATE agent_profiles
            SET profile_version = ?, profile_json = ?, updated_at = ?
            WHERE agent_id = ?
            """,
            (
                updated_profile.profile_version,
                json.dumps(updated_profile.profile_json),
                updated_profile.updated_at.isoformat(),
                updated_profile.agent_id,
            ),
        )

        revision = AgentProfileRevision(
            agent_id=agent_id,
            patch_json=patch_json,
            source=source,
        )
        connection.execute(
            """
            INSERT INTO agent_profile_revisions (
                revision_id, agent_id, patch_json, source, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                revision.revision_id,
                revision.agent_id,
                json.dumps(revision.patch_json),
                revision.source,
                revision.created_at.isoformat(),
            ),
        )
        return updated_profile, revision

    @staticmethod
    def _row_to_agent_profile(row: sqlite3.Row) -> AgentProfile:
        return AgentProfile(
            agent_id=row["agent_id"],
            name=row["name"],
            status=row["status"],
            profile_version=int(row["profile_version"]),
            profile_json=json.loads(row["profile_json"]),
            policy_json=json.loads(row["policy_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_agent_learning_event(row: sqlite3.Row) -> AgentLearningEvent:
        return AgentLearningEvent(
            event_id=row["event_id"],
            agent_id=row["agent_id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            status=row["status"],
            quality_passed=None if row["quality_passed"] is None else bool(row["quality_passed"]),
            issue_codes=json.loads(row["issue_codes_json"]),
            quality_score=float(row["quality_score"]),
            profile_digest=row["profile_digest"],
            memory_ids=json.loads(row["memory_ids_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_agent_profile_suggestion(row: sqlite3.Row) -> AgentProfileSuggestion:
        return AgentProfileSuggestion(
            suggestion_id=row["suggestion_id"],
            agent_id=row["agent_id"],
            patch_json=json.loads(row["patch_json"]),
            rationale_json=json.loads(row["rationale_json"]),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            applied_at=None if row["applied_at"] is None else datetime.fromisoformat(row["applied_at"]),
        )
