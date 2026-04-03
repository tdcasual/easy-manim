from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.task_service import CreateVideoTaskResult, TaskService
from video_agent.application.video_iteration_service import VideoIterationService
from video_agent.application.video_turn_service import VideoTurnService
from video_agent.domain.video_thread_models import (
    VideoIteration,
    VideoThread,
    VideoThreadParticipant,
    VideoTurn,
)


class VideoThreadCreationOutcome(BaseModel):
    thread: VideoThread
    iteration: VideoIteration
    turn: VideoTurn
    created_task: CreateVideoTaskResult | None = None


class VideoThreadTurnOutcome(BaseModel):
    thread: VideoThread
    iteration: VideoIteration
    turn: VideoTurn


class VideoThreadExplanationOutcome(BaseModel):
    thread: VideoThread
    iteration: VideoIteration
    owner_turn: VideoTurn
    agent_turn: VideoTurn


class VideoThreadSelectionOutcome(BaseModel):
    thread: VideoThread
    iteration: VideoIteration
    result_id: str


class VideoThreadParticipantMutationOutcome(BaseModel):
    thread_id: str
    participant: VideoThreadParticipant | None = None
    removed: bool = False


class VideoThreadService:
    def __init__(
        self,
        *,
        store: SQLiteTaskStore,
        iteration_service: VideoIterationService,
        turn_service: VideoTurnService,
        task_service: TaskService | None = None,
    ) -> None:
        self.store = store
        self.iteration_service = iteration_service
        self.turn_service = turn_service
        self.task_service = task_service

    def create_thread(
        self,
        *,
        owner_agent_id: str,
        title: str,
        prompt: str,
        session_id: str | None = None,
        memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> VideoThreadCreationOutcome:
        thread = self.store.upsert_video_thread(
            VideoThread(
                thread_id=f"thread-{uuid4()}",
                owner_agent_id=owner_agent_id,
                title=title,
                origin_prompt=prompt,
            )
        )
        self.store.upsert_video_thread_participant(
            VideoThreadParticipant(
                thread_id=thread.thread_id,
                participant_id="owner",
                participant_type="owner",
                agent_id=owner_agent_id,
                role="owner",
                display_name="Owner",
            )
        )
        iteration = self.iteration_service.create_iteration(
            thread_id=thread.thread_id,
            goal=prompt,
            requested_action="generate",
        )
        thread.current_iteration_id = iteration.iteration_id
        thread = self.store.upsert_video_thread(thread)
        turn = self.turn_service.append_owner_turn(
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            title=prompt,
            intent_type="generate",
        )
        created_task = None
        if self.task_service is not None:
            created_task = self.task_service.create_video_task(
                prompt=prompt,
                session_id=session_id,
                memory_ids=memory_ids,
                thread_id=thread.thread_id,
                iteration_id=iteration.iteration_id,
                execution_kind="initial_generation",
                agent_principal=agent_principal,
            )
        return VideoThreadCreationOutcome(
            thread=thread,
            iteration=iteration,
            turn=turn,
            created_task=created_task,
        )

    def load_thread(self, thread_id: str) -> VideoThread:
        thread = self.store.get_video_thread(thread_id)
        if thread is None:
            raise KeyError(f"Unknown thread_id: {thread_id}")
        return thread

    def append_turn(
        self,
        *,
        thread_id: str,
        iteration_id: str,
        title: str,
        summary: str = "",
        addressed_participant_id: str | None = None,
        reply_to_turn_id: str | None = None,
        related_result_id: str | None = None,
    ) -> VideoThreadTurnOutcome:
        thread = self.load_thread(thread_id)
        iteration = self._load_thread_iteration(thread_id=thread_id, iteration_id=iteration_id)
        target_result_id = self._resolve_iteration_target_result_id(
            thread_id=thread_id,
            iteration_id=iteration.iteration_id,
        )
        addressed_participant = self._resolve_addressed_participant(
            thread_id=thread_id,
            iteration=iteration,
            explicit_participant_id=addressed_participant_id,
        )
        turn = self.turn_service.append_owner_turn(
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            title=title,
            summary=summary,
            intent_type="discuss",
            related_result_id=related_result_id or target_result_id,
            reply_to_turn_id=reply_to_turn_id,
            addressed_participant_id=(
                None if addressed_participant is None else addressed_participant.participant_id
            ),
            addressed_agent_id=None if addressed_participant is None else addressed_participant.agent_id,
        )
        return VideoThreadTurnOutcome(
            thread=thread,
            iteration=iteration,
            turn=turn,
        )

    def list_participants(self, thread_id: str) -> list[VideoThreadParticipant]:
        self.load_thread(thread_id)
        return self.store.list_video_thread_participants(thread_id)

    def upsert_participant(
        self,
        *,
        thread_id: str,
        participant_id: str,
        participant_type: str,
        role: str,
        display_name: str,
        agent_id: str | None = None,
        capabilities: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> VideoThreadParticipantMutationOutcome:
        self._require_thread_owner(thread_id, agent_principal)
        participant = self.store.upsert_video_thread_participant(
            VideoThreadParticipant(
                thread_id=thread_id,
                participant_id=participant_id,
                participant_type=participant_type,  # type: ignore[arg-type]
                agent_id=agent_id,
                role=role,
                display_name=display_name,
                capabilities=list(capabilities or []),
            )
        )
        return VideoThreadParticipantMutationOutcome(
            thread_id=thread_id,
            participant=participant,
            removed=False,
        )

    def remove_participant(
        self,
        *,
        thread_id: str,
        participant_id: str,
        agent_principal: AgentPrincipal | None = None,
    ) -> VideoThreadParticipantMutationOutcome:
        self._require_thread_owner(thread_id, agent_principal)
        removed = self.store.delete_video_thread_participant(thread_id, participant_id)
        return VideoThreadParticipantMutationOutcome(
            thread_id=thread_id,
            participant=None,
            removed=removed,
        )

    def request_explanation(
        self,
        *,
        thread_id: str,
        iteration_id: str,
        summary: str,
    ) -> VideoThreadExplanationOutcome:
        thread = self.load_thread(thread_id)
        iteration = self._load_thread_iteration(thread_id=thread_id, iteration_id=iteration_id)
        latest_run = next(
            (
                run
                for run in reversed(self.store.list_video_agent_runs(thread_id))
                if run.iteration_id == iteration_id
            ),
            None,
        )
        latest_result = next(
            (
                result
                for result in reversed(self.store.list_video_results(thread_id))
                if result.iteration_id == iteration_id
            ),
            None,
        )
        addressed_participant = self._resolve_addressed_participant(
            thread_id=thread_id,
            iteration=iteration,
        )
        owner_turn = self.turn_service.append_owner_turn(
            thread_id=thread_id,
            iteration_id=iteration_id,
            title=summary,
            summary=summary,
            intent_type="request_explanation",
            related_result_id=None if latest_result is None else latest_result.result_id,
            addressed_participant_id=(
                None if addressed_participant is None else addressed_participant.participant_id
            ),
            addressed_agent_id=None if addressed_participant is None else addressed_participant.agent_id,
        )
        agent_turn = self.turn_service.append_agent_explanation_turn(
            thread_id=thread_id,
            iteration_id=iteration_id,
            title="Visible explanation",
            summary=self._build_explanation_summary(
                iteration=iteration,
                latest_result_summary=None if latest_result is None else latest_result.result_summary,
            ),
            speaker_agent_id=(
                latest_run.agent_id
                if latest_run is not None
                else iteration.responsible_agent_id
                or (None if addressed_participant is None else addressed_participant.agent_id)
                or "explainer"
            ),
            speaker_role=(
                latest_run.role
                if latest_run is not None
                else iteration.responsible_role
                or (None if addressed_participant is None else addressed_participant.role)
                or "planner"
            ),
            intent_type="request_explanation",
            reply_to_turn_id=owner_turn.turn_id,
            related_result_id=None if latest_result is None else latest_result.result_id,
        )
        self.store.upsert_video_thread_participant(
            VideoThreadParticipant(
                thread_id=thread_id,
                participant_id=agent_turn.speaker_agent_id or "explainer",
                participant_type="agent",
                agent_id=agent_turn.speaker_agent_id,
                role=agent_turn.speaker_role or "planner",
                display_name=(agent_turn.speaker_role or "planner").replace("_", " ").strip().title(),
            )
        )
        return VideoThreadExplanationOutcome(
            thread=thread,
            iteration=iteration,
            owner_turn=owner_turn,
            agent_turn=agent_turn,
        )

    def select_result(self, thread_id: str, result_id: str) -> VideoThreadSelectionOutcome:
        thread = self.load_thread(thread_id)
        result = self.iteration_service.load_result(result_id)
        if result.thread_id != thread_id:
            raise KeyError("result_thread_mismatch")
        result.selected = True
        self.store.upsert_video_result(result)
        thread.selected_result_id = result.result_id
        thread.current_iteration_id = result.iteration_id
        updated_thread = self.store.upsert_video_thread(thread)
        iteration = self._load_thread_iteration(thread_id=thread_id, iteration_id=result.iteration_id)
        iteration.selected_result_id = result.result_id
        self.store.upsert_video_iteration(iteration)
        return VideoThreadSelectionOutcome(
            thread=updated_thread,
            iteration=iteration,
            result_id=result.result_id,
        )

    def request_revision(
        self,
        *,
        thread_id: str,
        summary: str,
        base_task_id: str | None = None,
        base_iteration_id: str | None = None,
        preserve_working_parts: bool = True,
        session_id: str | None = None,
        memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> VideoThreadCreationOutcome:
        if self.task_service is None:
            raise RuntimeError("video_thread_task_service_not_configured")
        thread = self.load_thread(thread_id)
        parent_iteration_id = base_iteration_id or thread.current_iteration_id
        if parent_iteration_id is None:
            raise KeyError("thread_iteration_not_found")
        source_result_id = self._resolve_iteration_target_result_id(
            thread_id=thread_id,
            iteration_id=parent_iteration_id,
        )
        resolved_base_task_id = base_task_id or self._resolve_latest_iteration_task_id(
            thread_id=thread_id,
            iteration_id=parent_iteration_id,
        )
        parent_iteration = self._load_thread_iteration(thread_id=thread_id, iteration_id=parent_iteration_id)
        continuity_target = self._resolve_iteration_continuity_target(
            thread_id=thread_id,
            iteration=parent_iteration,
        )
        iteration = self.iteration_service.create_iteration(
            thread_id=thread_id,
            goal=summary,
            parent_iteration_id=parent_iteration_id,
            requested_action="revise",
            source_result_id=source_result_id,
            preserve_working_parts=preserve_working_parts,
        )
        if continuity_target["agent_role"] is not None:
            iteration = self.iteration_service.assign_responsibility(
                iteration.iteration_id,
                responsible_role=continuity_target["agent_role"],
                responsible_agent_id=continuity_target["agent_id"],
            )
        thread.current_iteration_id = iteration.iteration_id
        thread = self.store.upsert_video_thread(thread)
        turn = self.turn_service.append_owner_turn(
            thread_id=thread_id,
            iteration_id=iteration.iteration_id,
            title=summary,
            intent_type="request_revision",
            related_result_id=source_result_id,
            addressed_participant_id=continuity_target["participant_id"],
            addressed_agent_id=continuity_target["agent_id"],
        )
        created_task = self.task_service.revise_video_task(
            resolved_base_task_id,
            feedback=summary,
            preserve_working_parts=preserve_working_parts,
            session_id=session_id,
            memory_ids=memory_ids,
            thread_id=thread_id,
            iteration_id=iteration.iteration_id,
            execution_kind="revision",
            target_participant_id=continuity_target["participant_id"],
            target_agent_id=continuity_target["agent_id"],
            target_agent_role=continuity_target["agent_role"],
            agent_principal=agent_principal,
        )
        return VideoThreadCreationOutcome(
            thread=thread,
            iteration=iteration,
            turn=turn,
            created_task=created_task,
        )

    def _resolve_latest_iteration_task_id(self, *, thread_id: str, iteration_id: str) -> str:
        for task in self.store.list_thread_tasks(thread_id):
            if task.iteration_id == iteration_id:
                return task.task_id
        raise KeyError("iteration_task_not_found")

    def _resolve_iteration_target_result_id(self, *, thread_id: str, iteration_id: str) -> str | None:
        iteration = self._load_thread_iteration(thread_id=thread_id, iteration_id=iteration_id)
        if iteration.selected_result_id is not None:
            return iteration.selected_result_id
        results = self.store.list_video_results(thread_id)
        selected = next(
            (
                result.result_id
                for result in reversed(results)
                if result.iteration_id == iteration_id and result.selected
            ),
            None,
        )
        if selected is not None:
            return selected
        return next(
            (
                result.result_id
                for result in reversed(results)
                if result.iteration_id == iteration_id
            ),
            None,
        )

    def _load_thread_iteration(self, *, thread_id: str, iteration_id: str) -> VideoIteration:
        iteration = self.iteration_service.load_iteration(iteration_id)
        if iteration.thread_id != thread_id:
            raise KeyError("iteration_thread_mismatch")
        return iteration

    def _resolve_addressed_participant(
        self,
        *,
        thread_id: str,
        iteration: VideoIteration,
        explicit_participant_id: str | None = None,
    ) -> VideoThreadParticipant | None:
        participants = self.store.list_video_thread_participants(thread_id)
        participant_by_id = {participant.participant_id: participant for participant in participants}
        participant_by_agent_id = {
            participant.agent_id: participant
            for participant in participants
            if participant.agent_id is not None
        }
        if explicit_participant_id is not None:
            participant = participant_by_id.get(explicit_participant_id)
            if participant is None:
                raise KeyError("thread_participant_not_found")
            return participant

        if iteration.responsible_agent_id is not None:
            participant = participant_by_agent_id.get(iteration.responsible_agent_id)
            if participant is not None:
                return participant

        turns = self.store.list_video_turns(thread_id)
        scoped_turns = [turn for turn in turns if turn.iteration_id == iteration.iteration_id]
        participant = self._participant_from_addressed_turn(
            turns=scoped_turns,
            participant_by_id=participant_by_id,
        )
        if participant is not None:
            return participant

        runs = self.store.list_video_agent_runs(thread_id)
        participant = self._participant_from_runs(
            runs=[run for run in runs if run.iteration_id == iteration.iteration_id],
            participant_by_agent_id=participant_by_agent_id,
        )
        if participant is not None:
            return participant

        participant = self._participant_from_agent_turns(
            turns=scoped_turns,
            participant_by_agent_id=participant_by_agent_id,
        )
        if participant is not None:
            return participant

        participant = self._participant_from_addressed_turn(
            turns=turns,
            participant_by_id=participant_by_id,
        )
        if participant is not None:
            return participant

        return self._participant_from_agent_turns(
            turns=turns,
            participant_by_agent_id=participant_by_agent_id,
        )

    def _resolve_iteration_continuity_target(
        self,
        *,
        thread_id: str,
        iteration: VideoIteration,
    ) -> dict[str, str | None]:
        participant = self._resolve_addressed_participant(
            thread_id=thread_id,
            iteration=iteration,
        )
        if participant is not None:
            return {
                "participant_id": participant.participant_id,
                "agent_id": participant.agent_id,
                "agent_role": participant.role,
            }
        return {
            "participant_id": iteration.responsible_agent_id,
            "agent_id": iteration.responsible_agent_id,
            "agent_role": iteration.responsible_role,
        }

    @staticmethod
    def _participant_from_addressed_turn(
        *,
        turns: list[VideoTurn],
        participant_by_id: dict[str, VideoThreadParticipant],
    ) -> VideoThreadParticipant | None:
        for turn in reversed(turns):
            if turn.addressed_participant_id is None:
                continue
            participant = participant_by_id.get(turn.addressed_participant_id)
            if participant is not None:
                return participant
        return None

    @staticmethod
    def _participant_from_runs(
        *,
        runs,
        participant_by_agent_id: dict[str, VideoThreadParticipant],
    ) -> VideoThreadParticipant | None:
        for run in reversed(runs):
            participant = participant_by_agent_id.get(run.agent_id)
            if participant is not None:
                return participant
        return None

    @staticmethod
    def _participant_from_agent_turns(
        *,
        turns: list[VideoTurn],
        participant_by_agent_id: dict[str, VideoThreadParticipant],
    ) -> VideoThreadParticipant | None:
        for turn in reversed(turns):
            if turn.speaker_agent_id is None or turn.speaker_type != "agent":
                continue
            participant = participant_by_agent_id.get(turn.speaker_agent_id)
            if participant is not None:
                return participant
        return None

    def _require_thread_owner(
        self,
        thread_id: str,
        agent_principal: AgentPrincipal | None,
    ) -> VideoThread:
        thread = self.load_thread(thread_id)
        if agent_principal is None:
            return thread
        if agent_principal.agent_id != thread.owner_agent_id:
            raise PermissionError("agent_access_denied")
        return thread

    def _build_explanation_summary(
        self,
        *,
        iteration: VideoIteration,
        latest_result_summary: str | None,
    ) -> str:
        if latest_result_summary:
            return (
                "The current version favors this direction because it supports "
                f"'{latest_result_summary}' while staying aligned with '{iteration.goal}'."
            )
        return (
            "The current direction stays focused on "
            f"'{iteration.goal}' and keeps the visible animation choices coherent for the next revision."
        )
