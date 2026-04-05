from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentToken
from video_agent.domain.agent_session_models import AgentSession
from video_agent.domain.session_memory_models import SessionMemorySnapshot


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


class SQLiteAgentRuntimeStoreMixin:
    def issue_agent_token(self, token: AgentToken) -> None:
        token.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_tokens (
                    token_hash, agent_id, status, scopes_json, override_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token_hash) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    status = excluded.status,
                    scopes_json = excluded.scopes_json,
                    override_json = excluded.override_json,
                    updated_at = excluded.updated_at
                """,
                (
                    token.token_hash,
                    token.agent_id,
                    token.status,
                    json.dumps(token.scopes_json),
                    json.dumps(token.override_json),
                    token.created_at.isoformat(),
                    token.updated_at.isoformat(),
                ),
            )

    def get_agent_token(self, token_hash: str) -> Optional[AgentToken]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT token_hash, agent_id, status, scopes_json, override_json, created_at, updated_at
                FROM agent_tokens
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_token(row)

    def list_agent_tokens(self, agent_id: str) -> list[AgentToken]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT token_hash, agent_id, status, scopes_json, override_json, created_at, updated_at
                FROM agent_tokens
                WHERE agent_id = ?
                ORDER BY created_at ASC
                """,
                (agent_id,),
            ).fetchall()
        return [self._row_to_agent_token(row) for row in rows]

    def disable_agent_token(self, token_hash: str) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE agent_tokens
                SET status = ?, updated_at = ?
                WHERE token_hash = ?
                """,
                ("disabled", _utcnow_iso(), token_hash),
            )
        return result.rowcount > 0

    def create_agent_session(self, session: AgentSession) -> AgentSession:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_sessions (
                    session_id, session_hash, agent_id, token_hash, status, created_at, expires_at, last_seen_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.session_hash,
                    session.agent_id,
                    session.token_hash,
                    session.status,
                    session.created_at.isoformat(),
                    session.expires_at.isoformat(),
                    session.last_seen_at.isoformat(),
                    None if session.revoked_at is None else session.revoked_at.isoformat(),
                ),
            )
        return session

    def get_agent_session(self, session_hash: str) -> Optional[AgentSession]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id, session_hash, agent_id, token_hash, status, created_at, expires_at, last_seen_at, revoked_at
                FROM agent_sessions
                WHERE session_hash = ?
                """,
                (session_hash,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_session(row)

    def get_agent_session_by_id(self, session_id: str) -> Optional[AgentSession]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    session_id, session_hash, agent_id, token_hash, status, created_at, expires_at, last_seen_at, revoked_at
                FROM agent_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_session(row)

    def touch_agent_session(self, session_hash: str) -> Optional[AgentSession]:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE agent_sessions
                SET last_seen_at = ?
                WHERE session_hash = ?
                """,
                (_utcnow_iso(), session_hash),
            )
        return self.get_agent_session(session_hash)

    def revoke_agent_session(self, session_hash: str) -> bool:
        revoked_at = _utcnow_iso()
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE agent_sessions
                SET status = ?, revoked_at = ?
                WHERE session_hash = ?
                """,
                ("revoked", revoked_at, session_hash),
            )
        return result.rowcount > 0

    def create_agent_memory(self, record: AgentMemoryRecord) -> AgentMemoryRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_memories (
                    memory_id, agent_id, source_session_id, status, summary_text, summary_digest,
                    lineage_refs_json, snapshot_json, enhancement_json, created_at, disabled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_id,
                    record.agent_id,
                    record.source_session_id,
                    record.status,
                    record.summary_text,
                    record.summary_digest,
                    json.dumps(record.lineage_refs),
                    json.dumps(record.snapshot),
                    json.dumps(record.enhancement),
                    record.created_at.isoformat(),
                    None if record.disabled_at is None else record.disabled_at.isoformat(),
                ),
            )
        return record

    def get_agent_memory(self, memory_id: str) -> Optional[AgentMemoryRecord]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    memory_id, agent_id, source_session_id, status, summary_text, summary_digest,
                    lineage_refs_json, snapshot_json, enhancement_json, created_at, disabled_at
                FROM agent_memories
                WHERE memory_id = ?
                """,
                (memory_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_agent_memory(row)

    def list_agent_memories(self, agent_id: str, include_disabled: bool = False) -> list[AgentMemoryRecord]:
        query = """
            SELECT
                memory_id, agent_id, source_session_id, status, summary_text, summary_digest,
                lineage_refs_json, snapshot_json, enhancement_json, created_at, disabled_at
            FROM agent_memories
            WHERE agent_id = ?
        """
        params: list[Any] = [agent_id]
        if not include_disabled:
            query += " AND status = ?"
            params.append("active")
        query += " ORDER BY created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_agent_memory(row) for row in rows]

    def disable_agent_memory(self, memory_id: str) -> bool:
        disabled_at = _utcnow_iso()
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE agent_memories
                SET status = ?, disabled_at = ?
                WHERE memory_id = ?
                """,
                ("disabled", disabled_at, memory_id),
            )
        return result.rowcount > 0

    def upsert_session_memory_snapshot(self, snapshot: SessionMemorySnapshot) -> SessionMemorySnapshot:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM session_memory_snapshots WHERE session_id = ?",
                (snapshot.session_id,),
            ).fetchone()
            created_at = existing["created_at"] if existing is not None else _utcnow_iso()
            updated_at = _utcnow_iso()
            connection.execute(
                """
                INSERT INTO session_memory_snapshots (
                    session_id, agent_id, snapshot_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    agent_id = excluded.agent_id,
                    snapshot_json = excluded.snapshot_json,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.agent_id,
                    snapshot.model_dump_json(),
                    created_at,
                    updated_at,
                ),
            )
        return snapshot

    def get_session_memory_snapshot(self, session_id: str) -> SessionMemorySnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json
                FROM session_memory_snapshots
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionMemorySnapshot.model_validate_json(row["snapshot_json"])

    def list_session_memory_snapshots(self, agent_id: str | None = None) -> list[SessionMemorySnapshot]:
        query = """
            SELECT snapshot_json
            FROM session_memory_snapshots
        """
        params: list[Any] = []
        if agent_id is not None:
            query += " WHERE agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY updated_at ASC, created_at ASC, session_id ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [SessionMemorySnapshot.model_validate_json(row["snapshot_json"]) for row in rows]

    @staticmethod
    def _row_to_agent_token(row: sqlite3.Row) -> AgentToken:
        return AgentToken(
            token_hash=row["token_hash"],
            agent_id=row["agent_id"],
            status=row["status"],
            scopes_json=json.loads(row["scopes_json"]),
            override_json=json.loads(row["override_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_agent_session(row: sqlite3.Row) -> AgentSession:
        return AgentSession(
            session_id=row["session_id"],
            session_hash=row["session_hash"],
            agent_id=row["agent_id"],
            token_hash=row["token_hash"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            revoked_at=None if row["revoked_at"] is None else datetime.fromisoformat(row["revoked_at"]),
        )

    @staticmethod
    def _row_to_agent_memory(row: sqlite3.Row) -> AgentMemoryRecord:
        return AgentMemoryRecord(
            memory_id=row["memory_id"],
            agent_id=row["agent_id"],
            source_session_id=row["source_session_id"],
            status=row["status"],
            summary_text=row["summary_text"],
            summary_digest=row["summary_digest"],
            lineage_refs=json.loads(row["lineage_refs_json"]),
            snapshot=json.loads(row["snapshot_json"]),
            enhancement=json.loads(row["enhancement_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            disabled_at=None if row["disabled_at"] is None else datetime.fromisoformat(row["disabled_at"]),
        )
