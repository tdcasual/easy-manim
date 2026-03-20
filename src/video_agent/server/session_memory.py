from __future__ import annotations

from uuid import uuid4

from video_agent.domain.session_memory_models import SessionHandle, SessionMemorySnapshot


class SessionMemoryRegistry:
    def __init__(self) -> None:
        self._handles_by_session_key: dict[str, SessionHandle] = {}
        self._snapshots_by_session_id: dict[str, SessionMemorySnapshot] = {}

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
            snapshot = self._snapshots_by_session_id.get(handle.session_id)
            if snapshot is not None:
                self._store_snapshot(
                    snapshot.model_copy(update={"agent_id": agent_id})
                )

        return handle

    def get_session_id(self, session_key: str) -> str | None:
        handle = self._handles_by_session_key.get(session_key)
        return None if handle is None else handle.session_id

    def find_snapshot(self, session_id: str) -> SessionMemorySnapshot | None:
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
        self._store_snapshot(stored)
        return stored.model_copy(deep=True)

    def clear_session(self, session_id: str) -> SessionMemorySnapshot:
        snapshot = self.get_snapshot(session_id)
        cleared = snapshot.model_copy(update={"entries": []}, deep=True)
        self._store_snapshot(cleared)
        return cleared.model_copy(deep=True)

    def list_snapshots(self, agent_id: str | None = None) -> list[SessionMemorySnapshot]:
        snapshots = [snapshot.model_copy(deep=True) for snapshot in self._snapshots_by_session_id.values()]
        if agent_id is None:
            return snapshots
        return [snapshot for snapshot in snapshots if snapshot.agent_id == agent_id]

    def _store_snapshot(self, snapshot: SessionMemorySnapshot) -> None:
        self._snapshots_by_session_id.pop(snapshot.session_id, None)
        self._snapshots_by_session_id[snapshot.session_id] = snapshot.model_copy(deep=True)
