from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.case_memory_service import CaseMemoryService
from video_agent.application.persistent_memory_service import PersistentMemoryService
from video_agent.application.task_memory_context import (
    apply_persistent_memory_context_to_task,
    persistent_memory_digest_from_task,
    persistent_memory_ids_from_task,
    persistent_memory_summary_from_task,
)
from video_agent.application.task_service import CreateVideoTaskResult, TaskService, VideoTaskSnapshot
from video_agent.application.workflow_collaboration_memory import (
    build_workflow_memory_context,
    build_workflow_memory_query,
)
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.models import VideoTask
from video_agent.domain.review_workflow_models import (
    CollaborationEventRecord,
    WorkflowCollaborationMemoryContext,
    WorkflowMemoryPinState,
    WorkflowMemoryRecommendation,
    WorkflowMemoryRecommendations,
    WorkflowMemoryState,
    RuntimeCollaborationSummary,
    WorkflowCollaborationSummary,
    WorkflowParticipant,
)


@dataclass(frozen=True)
class WorkflowDecisionAuthorization:
    actor_agent_id: str | None
    owner_submission: bool


class WorkflowCollaborationService:
    COLLABORATION_EVENT_TYPES = frozenset(
        {
            "workflow_participant_upserted",
            "workflow_participant_removed",
            "workflow_memory_pinned",
            "workflow_memory_unpinned",
        }
    )

    def __init__(
        self,
        *,
        store: SQLiteTaskStore,
        task_service: TaskService,
        persistent_memory_service: PersistentMemoryService | None = None,
        case_memory_service: CaseMemoryService | None = None,
    ) -> None:
        self.store = store
        self.task_service = task_service
        self.persistent_memory_service = persistent_memory_service
        self.case_memory_service = case_memory_service

    def require_workflow_access(
        self,
        task_id: str,
        agent_id: str,
        *,
        capability: str,
    ) -> VideoTask:
        task = self._require_task(task_id)
        if task.agent_id == agent_id:
            return task
        root_task_id = task.root_task_id or task.task_id
        participant = self.store.get_workflow_participant(root_task_id, agent_id)
        if participant is not None and participant.has_capability(capability):
            return task
        raise PermissionError("agent_access_denied")

    def authorize_review_decision(
        self,
        task_id: str,
        agent_principal: AgentPrincipal | None,
    ) -> WorkflowDecisionAuthorization:
        actor_agent_id = None if agent_principal is None else agent_principal.agent_id
        if actor_agent_id is None:
            return WorkflowDecisionAuthorization(actor_agent_id=None, owner_submission=True)
        task = self.require_workflow_access(
            task_id,
            actor_agent_id,
            capability="review_decision:write",
        )
        return WorkflowDecisionAuthorization(
            actor_agent_id=actor_agent_id,
            owner_submission=task.agent_id == actor_agent_id,
        )

    def list_workflow_participants(
        self,
        task_id: str,
        *,
        agent_principal: AgentPrincipal | None = None,
    ) -> tuple[str, list[WorkflowParticipant]]:
        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:read",
        )
        root_task_id = task.root_task_id or task.task_id
        return root_task_id, self.store.list_workflow_participants(root_task_id)

    def upsert_workflow_participant(
        self,
        task_id: str,
        *,
        participant_agent_id: str,
        role: str,
        capabilities: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> WorkflowParticipant:
        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:mutate",
        )
        root_task_id = task.root_task_id or task.task_id
        participant = WorkflowParticipant(
            root_task_id=root_task_id,
            agent_id=participant_agent_id,
            role=role,
            capabilities=list(capabilities or []),
        )
        persisted = self.store.upsert_workflow_participant(participant)
        self.store.append_event(
            root_task_id,
            "workflow_participant_upserted",
            {
                "root_task_id": root_task_id,
                "agent_id": persisted.agent_id,
                "role": persisted.role,
                "capabilities": list(persisted.capabilities),
            },
        )
        return persisted

    def remove_workflow_participant(
        self,
        task_id: str,
        *,
        participant_agent_id: str,
        agent_principal: AgentPrincipal | None = None,
    ) -> tuple[str, bool]:
        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:mutate",
        )
        root_task_id = task.root_task_id or task.task_id
        removed = self.store.delete_workflow_participant(root_task_id, participant_agent_id)
        if removed:
            self.store.append_event(
                root_task_id,
                "workflow_participant_removed",
                {
                    "root_task_id": root_task_id,
                    "agent_id": participant_agent_id,
                    "removed": True,
                },
            )
        return root_task_id, removed

    def accept_best_version(self, task_id: str, *, actor_agent_id: str) -> VideoTaskSnapshot:
        accepted_task = self.require_workflow_access(
            task_id,
            actor_agent_id,
            capability="review_decision:write",
        )
        return self.task_service.accept_authorized_task(accepted_task)

    def list_workflow_memory_recommendations(
        self,
        task_id: str,
        *,
        limit: int = 5,
        agent_principal: AgentPrincipal | None = None,
    ) -> WorkflowMemoryRecommendations:
        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:read",
        )
        root_task = self._require_task(task.root_task_id or task.task_id)
        query = build_workflow_memory_query(
            root_task=root_task,
            case_memory=self._load_case_memory(root_task.task_id),
        )
        pinned_memory_ids = persistent_memory_ids_from_task(root_task)
        if self.persistent_memory_service is None or not root_task.agent_id:
            return WorkflowMemoryRecommendations(
                root_task_id=root_task.task_id,
                query=query,
                pinned_memory_ids=pinned_memory_ids,
            )

        hits = self.persistent_memory_service.query_agent_memories(
            root_task.agent_id,
            query=query,
            limit=limit,
        )
        return WorkflowMemoryRecommendations(
            root_task_id=root_task.task_id,
            query=query,
            pinned_memory_ids=pinned_memory_ids,
            items=[
                WorkflowMemoryRecommendation(
                    **hit.model_dump(mode="json"),
                    pinned=hit.memory_id in pinned_memory_ids,
                )
                for hit in hits
            ],
        )

    def pin_workflow_memory(
        self,
        task_id: str,
        *,
        memory_id: str,
        agent_principal: AgentPrincipal | None = None,
    ) -> WorkflowMemoryPinState:
        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:mutate",
        )
        root_task = self._require_task(task.root_task_id or task.task_id)
        previous_memory_ids = persistent_memory_ids_from_task(root_task)
        pinned_memory_ids = list(dict.fromkeys(previous_memory_ids + [memory_id]))
        state = self._update_root_workflow_memory(
            root_task=root_task,
            memory_ids=pinned_memory_ids,
        )
        if memory_id not in previous_memory_ids:
            self.store.append_event(
                root_task.task_id,
                "workflow_memory_pinned",
                {
                    "root_task_id": root_task.task_id,
                    "agent_id": root_task.agent_id,
                    "memory_id": memory_id,
                    "pinned_memory_ids": list(state.pinned_memory_ids),
                },
            )
        return WorkflowMemoryPinState(
            memory_id=memory_id,
            **state.model_dump(mode="json"),
        )

    def unpin_workflow_memory(
        self,
        task_id: str,
        *,
        memory_id: str,
        agent_principal: AgentPrincipal | None = None,
    ) -> WorkflowMemoryPinState:
        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:mutate",
        )
        root_task = self._require_task(task.root_task_id or task.task_id)
        previous_memory_ids = persistent_memory_ids_from_task(root_task)
        pinned_memory_ids = [item for item in previous_memory_ids if item != memory_id]
        state = self._update_root_workflow_memory(
            root_task=root_task,
            memory_ids=pinned_memory_ids,
        )
        if memory_id in previous_memory_ids:
            self.store.append_event(
                root_task.task_id,
                "workflow_memory_unpinned",
                {
                    "root_task_id": root_task.task_id,
                    "agent_id": root_task.agent_id,
                    "memory_id": memory_id,
                    "pinned_memory_ids": list(state.pinned_memory_ids),
                },
            )
        return WorkflowMemoryPinState(
            memory_id=memory_id,
            **state.model_dump(mode="json"),
        )

    def apply_workflow_memory_updates(
        self,
        task_id: str,
        *,
        pin_memory_ids: list[str] | None = None,
        unpin_memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> WorkflowMemoryState | None:
        normalized_unpin_ids = list(dict.fromkeys(unpin_memory_ids or []))
        normalized_pin_ids = list(dict.fromkeys(pin_memory_ids or []))
        if not normalized_unpin_ids and not normalized_pin_ids:
            return None

        task = self.task_service.require_owner_task(
            task_id,
            agent_principal,
            action="task:mutate",
        )
        root_task_id = task.root_task_id or task.task_id
        for memory_id in normalized_unpin_ids:
            self.unpin_workflow_memory(
                root_task_id,
                memory_id=memory_id,
                agent_principal=agent_principal,
            )
        for memory_id in normalized_pin_ids:
            self.pin_workflow_memory(
                root_task_id,
                memory_id=memory_id,
                agent_principal=agent_principal,
            )
        return self._build_workflow_memory_state(self._require_task(root_task_id))

    def build_workflow_summary(
        self,
        task_id: str,
        *,
        recent_event_limit: int = 10,
    ) -> WorkflowCollaborationSummary:
        task = self._require_task(task_id)
        root_task_id = task.root_task_id or task.task_id
        participants = self.store.list_workflow_participants(root_task_id)
        recent_events = self._load_recent_collaboration_events(
            [root_task_id],
            limit=recent_event_limit,
        )
        return WorkflowCollaborationSummary(
            root_task_id=root_task_id,
            participant_count=len(participants),
            participants_by_role=self._count_roles(participants),
            capability_counts=self._count_capabilities(participants),
            participants=participants,
            recent_events=recent_events,
        )

    def build_runtime_summary(
        self,
        *,
        recent_event_limit: int = 10,
    ) -> RuntimeCollaborationSummary:
        root_task_ids = [task.task_id for task in self._list_root_tasks()]
        all_participants: list[WorkflowParticipant] = []
        for root_task_id in root_task_ids:
            all_participants.extend(self.store.list_workflow_participants(root_task_id))
        recent_events = self._load_recent_collaboration_events(
            root_task_ids,
            limit=recent_event_limit,
        )
        return RuntimeCollaborationSummary(
            workflow_count=len(root_task_ids),
            participant_count=len(all_participants),
            participants_by_role=self._count_roles(all_participants),
            capability_counts=self._count_capabilities(all_participants),
            recent_events=recent_events,
        )

    def build_workflow_memory_context(self, task_id: str) -> WorkflowCollaborationMemoryContext:
        task = self._require_task(task_id)
        root_task = self._require_task(task.root_task_id or task.task_id)
        shared_records = self._load_shared_memory_records(
            agent_id=root_task.agent_id,
            memory_ids=list(
                dict.fromkeys(
                    persistent_memory_ids_from_task(task)
                    + persistent_memory_ids_from_task(root_task)
                )
            ),
        )
        case_memory = self._load_case_memory(root_task.task_id)
        return build_workflow_memory_context(
            task=task,
            root_task=root_task,
            shared_records=shared_records,
            case_memory=case_memory,
        )

    def revise_video_task(
        self,
        task_id: str,
        *,
        feedback: str,
        actor_agent_id: str,
        preserve_working_parts: bool = True,
        session_id: str | None = None,
        memory_ids: list[str] | None = None,
    ) -> CreateVideoTaskResult:
        base_task = self.require_workflow_access(
            task_id,
            actor_agent_id,
            capability="review_decision:write",
        )
        persistent_memory = self._resolve_collaboration_persistent_memory(
            base_task=base_task,
            actor_agent_id=actor_agent_id,
            memory_ids=memory_ids,
        )
        return self.task_service.revise_authorized_task(
            base_task=base_task,
            feedback=feedback,
            preserve_working_parts=preserve_working_parts,
            session_id=session_id,
            persistent_memory=persistent_memory,
        )

    def retry_video_task(
        self,
        task_id: str,
        *,
        actor_agent_id: str,
        session_id: str | None = None,
    ) -> CreateVideoTaskResult:
        base_task = self.require_workflow_access(
            task_id,
            actor_agent_id,
            capability="review_decision:write",
        )
        return self.task_service.retry_authorized_task(
            base_task=base_task,
            session_id=session_id,
        )

    def _require_task(self, task_id: str) -> VideoTask:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        return task

    def _list_root_tasks(self) -> list[VideoTask]:
        roots: list[VideoTask] = []
        seen: set[str] = set()
        for row in self.store.list_tasks(limit=None, order_by="updated_at"):
            task = self.store.get_task(row["task_id"])
            if task is None or task.task_id in seen:
                continue
            if (task.root_task_id or task.task_id) != task.task_id:
                continue
            seen.add(task.task_id)
            roots.append(task)
        return roots

    @classmethod
    def _count_roles(cls, participants: list[WorkflowParticipant]) -> dict[str, int]:
        counts = Counter(participant.role for participant in participants)
        return dict(sorted(counts.items()))

    @classmethod
    def _count_capabilities(cls, participants: list[WorkflowParticipant]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for participant in participants:
            for capability in sorted(set(participant.capabilities)):
                counts[capability] += 1
        return dict(sorted(counts.items()))

    def _load_recent_collaboration_events(
        self,
        root_task_ids: list[str],
        *,
        limit: int,
    ) -> list[CollaborationEventRecord]:
        records: list[CollaborationEventRecord] = []
        for root_task_id in root_task_ids:
            for event in self.store.list_events(root_task_id, limit=200):
                if event["event_type"] not in self.COLLABORATION_EVENT_TYPES:
                    continue
                payload = event.get("payload")
                payload_dict = payload if isinstance(payload, dict) else {}
                records.append(
                    CollaborationEventRecord(
                        root_task_id=str(payload_dict.get("root_task_id") or root_task_id),
                        event_type=event["event_type"],
                        created_at=datetime.fromisoformat(event["created_at"]),
                        agent_id=self._optional_text(payload_dict.get("agent_id")),
                        memory_id=self._optional_text(payload_dict.get("memory_id")),
                        role=self._optional_text(payload_dict.get("role")),
                        capabilities=self._normalize_capabilities(payload_dict.get("capabilities")),
                        removed=bool(payload_dict.get("removed")),
                    )
                )
        records.sort(key=lambda item: (item.created_at, item.root_task_id, item.event_type))
        if limit <= 0:
            return records
        return records[-limit:]

    def _load_shared_memory_records(
        self,
        *,
        agent_id: str | None,
        memory_ids: list[str],
    ) -> list[AgentMemoryRecord]:
        if self.persistent_memory_service is None or not agent_id:
            return []

        records: list[AgentMemoryRecord] = []
        for memory_id in memory_ids:
            try:
                record = self.persistent_memory_service.get_agent_memory(memory_id, agent_id=agent_id)
            except Exception:
                continue
            if record.status != "active":
                continue
            records.append(record)
        return records

    def _load_case_memory(self, root_task_id: str) -> dict[str, Any]:
        if self.case_memory_service is None:
            return {}
        payload = self.case_memory_service.get_case_memory(root_task_id)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _optional_text(value: object) -> str | None:
        text = str(value or "").strip()
        return text or None

    @staticmethod
    def _normalize_capabilities(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            capability = str(item).strip()
            if capability:
                normalized.append(capability)
        return normalized

    def _resolve_collaboration_persistent_memory(
        self,
        *,
        base_task: VideoTask,
        actor_agent_id: str,
        memory_ids: list[str] | None,
    ):
        if base_task.agent_id != actor_agent_id:
            if memory_ids:
                raise PermissionError("agent_access_denied")
            return self.task_service.inherit_persistent_memory_context(base_task)
        return self.task_service.resolve_persistent_memory_context_for_agent(actor_agent_id, memory_ids)

    def _update_root_workflow_memory(
        self,
        *,
        root_task: VideoTask,
        memory_ids: list[str],
    ) -> WorkflowMemoryState:
        agent_id = root_task.agent_id or ""
        persistent_memory = self.task_service.resolve_persistent_memory_context_for_agent(agent_id, memory_ids)
        apply_persistent_memory_context_to_task(root_task, persistent_memory)
        self.store.update_task(root_task)
        self.task_service.artifact_store.write_task_snapshot(root_task)
        return self._build_workflow_memory_state(root_task)

    @staticmethod
    def _build_workflow_memory_state(root_task: VideoTask) -> WorkflowMemoryState:
        return WorkflowMemoryState(
            root_task_id=root_task.task_id,
            pinned_memory_ids=persistent_memory_ids_from_task(root_task),
            persistent_memory_context_summary=persistent_memory_summary_from_task(root_task),
            persistent_memory_context_digest=persistent_memory_digest_from_task(root_task),
            task_memory_context=dict(root_task.task_memory_context),
        )
