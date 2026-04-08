from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from video_agent.domain.session_memory_models import (
    SessionHandle,
    SessionMemorySnapshot,
)


class SessionMemoryRegistry:
    def __init__(
        self,
        *,
        load_snapshot: Callable[[str], SessionMemorySnapshot | None] | None = None,
        persist_snapshot: Callable[[SessionMemorySnapshot], SessionMemorySnapshot] | None = None,
        list_persisted_snapshots: Callable[[str | None], list[SessionMemorySnapshot]] | None = None,
    ) -> None:
        self._handles_by_session_key: dict[str, SessionHandle] = {}
        self._snapshots_by_session_id: dict[str, SessionMemorySnapshot] = {}
        self._load_snapshot = load_snapshot
        self._persist_snapshot = persist_snapshot
        self._list_persisted_snapshots = list_persisted_snapshots

    def ensure_session(self, session_key: str, agent_id: str | None = None) -> SessionHandle:
        handle = self._handles_by_session_key.get(session_key)
        if handle is None:
            handle = SessionHandle(session_id=str(uuid4()), agent_id=agent_id)
            self._handles_by_session_key[session_key] = handle
            self._snapshots_by_session_id[handle.session_id] = SessionMemorySnapshot(
                session_id=handle.session_id,
                agent_id=agent_id,
            )
            return handle

        if agent_id is not None and handle.agent_id != agent_id:
            handle = handle.model_copy(update={"agent_id": agent_id})
            self._handles_by_session_key[session_key] = handle
            snapshot = self.find_snapshot(handle.session_id)
            if snapshot is not None:
                self.store_snapshot(
                    snapshot.model_copy(update={"agent_id": agent_id})
                )

        return handle

    def ensure_session_id(self, session_id: str, agent_id: str | None = None) -> SessionMemorySnapshot:
        snapshot = self.find_snapshot(session_id)
        if snapshot is None:
            snapshot = SessionMemorySnapshot(
                session_id=session_id,
                agent_id=agent_id,
            )
        elif agent_id is not None and snapshot.agent_id != agent_id:
            snapshot = snapshot.model_copy(update={"agent_id": agent_id}, deep=True)
        return self.store_snapshot(snapshot)

    def get_session_id(self, session_key: str) -> str | None:
        handle = self._handles_by_session_key.get(session_key)
        return None if handle is None else handle.session_id

    def find_snapshot(self, session_id: str) -> SessionMemorySnapshot | None:
        snapshot = self._snapshots_by_session_id.get(session_id)
        if snapshot is None and self._load_snapshot is not None:
            loaded = self._load_snapshot(session_id)
            if loaded is not None:
                self._store_snapshot(loaded)
                snapshot = self._snapshots_by_session_id.get(session_id)
        if snapshot is None:
            return None
        return snapshot.model_copy(deep=True)

    def get_snapshot(self, session_id: str) -> SessionMemorySnapshot:
        snapshot = self.find_snapshot(session_id)
        if snapshot is None:
            return SessionMemorySnapshot(session_id=session_id)
        return snapshot

    def store_snapshot(self, snapshot: SessionMemorySnapshot) -> SessionMemorySnapshot:
        stored = snapshot.model_copy(deep=True)
        if self._persist_snapshot is not None:
            stored = self._persist_snapshot(stored).model_copy(deep=True)
        self._store_snapshot(stored)
        return stored.model_copy(deep=True)

    def clear_session(self, session_id: str) -> SessionMemorySnapshot:
        snapshot = self.get_snapshot(session_id)
        cleared = snapshot.model_copy(update={"entries": []}, deep=True)
        return self.store_snapshot(cleared)

    def list_snapshots(self, agent_id: str | None = None) -> list[SessionMemorySnapshot]:
        snapshots_by_session_id: dict[str, SessionMemorySnapshot] = {}
        ordered_ids: list[str] = []

        if self._list_persisted_snapshots is not None:
            for snapshot in self._list_persisted_snapshots(agent_id):
                copied = snapshot.model_copy(deep=True)
                snapshots_by_session_id[copied.session_id] = copied
                ordered_ids.append(copied.session_id)
                self._store_snapshot(copied)

        for snapshot in self._snapshots_by_session_id.values():
            if agent_id is not None and snapshot.agent_id != agent_id:
                continue
            if snapshot.session_id not in snapshots_by_session_id:
                snapshots_by_session_id[snapshot.session_id] = snapshot.model_copy(deep=True)
                ordered_ids.append(snapshot.session_id)

        return [snapshots_by_session_id[session_id].model_copy(deep=True) for session_id in ordered_ids]

    def _store_snapshot(self, snapshot: SessionMemorySnapshot) -> None:
        self._snapshots_by_session_id.pop(snapshot.session_id, None)
        self._snapshots_by_session_id[snapshot.session_id] = snapshot.model_copy(deep=True)
