from __future__ import annotations

from uuid import uuid4

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.video_thread_models import VideoTurn


class VideoTurnService:
    def __init__(self, *, store: SQLiteTaskStore) -> None:
        self.store = store

    def append_owner_turn(
        self,
        *,
        thread_id: str,
        iteration_id: str,
        title: str,
        summary: str = "",
        intent_type: str | None = None,
        related_result_id: str | None = None,
        reply_to_turn_id: str | None = None,
        addressed_participant_id: str | None = None,
        addressed_agent_id: str | None = None,
    ) -> VideoTurn:
        turn = VideoTurn(
            turn_id=f"turn-{uuid4()}",
            thread_id=thread_id,
            iteration_id=iteration_id,
            turn_type="owner_request",
            intent_type=intent_type,
            speaker_type="owner",
            title=title,
            summary=summary,
            reply_to_turn_id=reply_to_turn_id,
            related_result_id=related_result_id,
            addressed_participant_id=addressed_participant_id,
            addressed_agent_id=addressed_agent_id,
        )
        return self.store.upsert_video_turn(turn)

    def append_agent_explanation_turn(
        self,
        *,
        thread_id: str,
        iteration_id: str,
        title: str,
        summary: str,
        speaker_agent_id: str,
        speaker_role: str,
        intent_type: str | None = None,
        reply_to_turn_id: str | None = None,
        related_result_id: str | None = None,
    ) -> VideoTurn:
        turn = VideoTurn(
            turn_id=f"turn-{uuid4()}",
            thread_id=thread_id,
            iteration_id=iteration_id,
            turn_type="agent_explanation",
            intent_type=intent_type,
            speaker_type="agent",
            speaker_agent_id=speaker_agent_id,
            speaker_role=speaker_role,
            title=title,
            summary=summary,
            reply_to_turn_id=reply_to_turn_id,
            related_result_id=related_result_id,
        )
        return self.store.upsert_video_turn(turn)
