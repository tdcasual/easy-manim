from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.case_memory_service import CaseMemoryService
from video_agent.application.persistent_memory_service import PersistentMemoryService
from video_agent.application.task_service import CreateVideoTaskResult, TaskService, VideoTaskSnapshot
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.models import VideoTask
from video_agent.domain.review_workflow_models import (
    CollaborationMemoryItem,
    CollaborationEventRecord,
    RoleCollaborationMemoryContext,
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
        query = self._build_workflow_memory_query(root_task)
        pinned_memory_ids = list(root_task.selected_memory_ids)
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
        previous_memory_ids = list(root_task.selected_memory_ids)
        pinned_memory_ids = list(dict.fromkeys(list(root_task.selected_memory_ids) + [memory_id]))
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
        previous_memory_ids = list(root_task.selected_memory_ids)
        pinned_memory_ids = [item for item in root_task.selected_memory_ids if item != memory_id]
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
        root_task_id = root_task.task_id
        shared_memory_ids = list(
            dict.fromkeys(
                list(task.selected_memory_ids)
                + list(root_task.selected_memory_ids)
            )
        )
        shared_records = self._load_shared_memory_records(
            agent_id=root_task.agent_id,
            memory_ids=shared_memory_ids,
        )
        task_context_summary = self._resolve_task_memory_context_summary(task=task, root_task=root_task)
        case_memory = self._load_case_memory(root_task_id)
        return WorkflowCollaborationMemoryContext(
            root_task_id=root_task_id,
            agent_id=root_task.agent_id,
            shared_memory_ids=shared_memory_ids,
            planner=self._build_role_memory_context(
                role="planner",
                shared_records=shared_records,
                task_context_summary=task_context_summary,
                case_memory=case_memory,
            ),
            reviewer=self._build_role_memory_context(
                role="reviewer",
                shared_records=shared_records,
                task_context_summary=task_context_summary,
                case_memory=case_memory,
            ),
            repairer=self._build_role_memory_context(
                role="repairer",
                shared_records=shared_records,
                task_context_summary=task_context_summary,
                case_memory=case_memory,
            ),
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

    @staticmethod
    def _resolve_task_memory_context_summary(*, task: VideoTask, root_task: VideoTask) -> str | None:
        for candidate in (
            task.persistent_memory_context_summary,
            root_task.persistent_memory_context_summary,
        ):
            text = str(candidate or "").strip()
            if text:
                return text
        return None

    def _load_case_memory(self, root_task_id: str) -> dict[str, Any]:
        if self.case_memory_service is None:
            return {}
        payload = self.case_memory_service.get_case_memory(root_task_id)
        return payload if isinstance(payload, dict) else {}

    def _build_role_memory_context(
        self,
        *,
        role: str,
        shared_records: list[AgentMemoryRecord],
        task_context_summary: str | None,
        case_memory: dict[str, Any],
    ) -> RoleCollaborationMemoryContext:
        items: list[CollaborationMemoryItem] = []
        for record in shared_records:
            items.append(
                CollaborationMemoryItem(
                    source="persistent_memory",
                    title=self._persistent_memory_title(role),
                    summary=record.summary_text.strip(),
                    memory_id=record.memory_id,
                )
            )
        if task_context_summary and not shared_records:
            items.append(
                CollaborationMemoryItem(
                    source="task_context",
                    title="Attached workflow memory",
                    summary=task_context_summary,
                )
            )
        items.extend(self._build_case_memory_items(role=role, case_memory=case_memory))
        summary = "\n".join(
            f"{item.title}: {item.summary}".strip()
            for item in items
            if item.summary.strip()
        ).strip()
        return RoleCollaborationMemoryContext(
            role=role,  # type: ignore[arg-type]
            summary=summary,
            item_count=len(items),
            items=items,
        )

    @staticmethod
    def _persistent_memory_title(role: str) -> str:
        titles = {
            "planner": "Shared planning memory",
            "reviewer": "Shared review memory",
            "repairer": "Shared repair memory",
        }
        return titles[role]

    @classmethod
    def _build_case_memory_items(
        cls,
        *,
        role: str,
        case_memory: dict[str, Any],
    ) -> list[CollaborationMemoryItem]:
        if role == "planner":
            return cls._planner_case_memory_items(case_memory)
        if role == "reviewer":
            return cls._reviewer_case_memory_items(case_memory)
        return cls._repairer_case_memory_items(case_memory)

    @staticmethod
    def _planner_case_memory_items(case_memory: dict[str, Any]) -> list[CollaborationMemoryItem]:
        items: list[CollaborationMemoryItem] = []
        for invariant in (case_memory.get("delivery_invariants") or [])[:2]:
            text = str(invariant).strip()
            if text:
                items.append(
                    CollaborationMemoryItem(
                        source="case_memory",
                        title="Delivery invariant",
                        summary=text,
                    )
                )
        notes = case_memory.get("planner_notes") or []
        if isinstance(notes, list) and notes:
            latest = notes[-1] if isinstance(notes[-1], dict) else {}
            generation_mode = str(latest.get("generation_mode") or "").strip()
            risk_level = str(latest.get("risk_level") or "").strip()
            parts = [f"generation_mode={generation_mode}" if generation_mode else "", f"risk_level={risk_level}" if risk_level else ""]
            summary = ", ".join(part for part in parts if part)
            if summary:
                items.append(
                    CollaborationMemoryItem(
                        source="case_memory",
                        title="Latest planner state",
                        summary=summary,
                    )
                )
        return items

    @staticmethod
    def _reviewer_case_memory_items(case_memory: dict[str, Any]) -> list[CollaborationMemoryItem]:
        items: list[CollaborationMemoryItem] = []
        findings = case_memory.get("review_findings") or []
        if not isinstance(findings, list):
            return items
        for finding in findings[-2:]:
            if not isinstance(finding, dict):
                continue
            quality_gate_status = str(finding.get("quality_gate_status") or "").strip()
            summary = str(finding.get("summary") or "").strip()
            must_fix = list(finding.get("must_fix_issue_codes", []) or [])
            parts = []
            if quality_gate_status:
                parts.append(f"quality_gate_status={quality_gate_status}")
            if summary:
                parts.append(summary)
            if must_fix:
                parts.append("must_fix=" + ", ".join(str(item) for item in must_fix[:3]))
            text = "; ".join(parts).strip()
            if text:
                items.append(
                    CollaborationMemoryItem(
                        source="case_memory",
                        title="Latest review finding",
                        summary=text,
                    )
                )
        return items

    @staticmethod
    def _repairer_case_memory_items(case_memory: dict[str, Any]) -> list[CollaborationMemoryItem]:
        items: list[CollaborationMemoryItem] = []
        constraints = case_memory.get("repair_constraints") or []
        if not isinstance(constraints, list):
            return items
        for constraint in constraints[-2:]:
            if not isinstance(constraint, dict):
                continue
            parts = []
            quality_gate_status = str(constraint.get("quality_gate_status") or "").strip()
            if quality_gate_status:
                parts.append(f"quality_gate_status={quality_gate_status}")
            summary = str(constraint.get("summary") or "").strip()
            if summary:
                parts.append(summary)
            repair_strategy = str(constraint.get("repair_strategy") or "").strip()
            if repair_strategy:
                parts.append(repair_strategy)
            recovery_action = str(constraint.get("recovery_selected_action") or "").strip()
            if recovery_action:
                parts.append(f"recovery_selected_action={recovery_action}")
            must_fix = list(constraint.get("must_fix_issue_codes", []) or [])
            if must_fix:
                parts.append("must_fix=" + ", ".join(str(item) for item in must_fix[:3]))
            text = "; ".join(parts).strip()
            if text:
                items.append(
                    CollaborationMemoryItem(
                        source="case_memory",
                        title="Latest repair constraint",
                        summary=text,
                    )
                )
        return items

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

    def _build_workflow_memory_query(self, root_task: VideoTask) -> str:
        parts = [str(root_task.prompt or "").strip()]
        case_memory = self._load_case_memory(root_task.task_id)
        review_findings = case_memory.get("review_findings") or []
        if isinstance(review_findings, list) and review_findings:
            latest_finding = review_findings[-1] if isinstance(review_findings[-1], dict) else {}
            summary = str(latest_finding.get("summary") or "").strip()
            if summary:
                parts.append(summary)
        repair_constraints = case_memory.get("repair_constraints") or []
        if isinstance(repair_constraints, list) and repair_constraints:
            latest_constraint = repair_constraints[-1] if isinstance(repair_constraints[-1], dict) else {}
            repair_strategy = str(latest_constraint.get("repair_strategy") or "").strip()
            if repair_strategy:
                parts.append(repair_strategy)
        return " ".join(part for part in parts if part).strip()

    def _update_root_workflow_memory(
        self,
        *,
        root_task: VideoTask,
        memory_ids: list[str],
    ) -> WorkflowMemoryState:
        agent_id = root_task.agent_id or ""
        persistent_memory = self.task_service.resolve_persistent_memory_context_for_agent(agent_id, memory_ids)
        root_task.selected_memory_ids = list(persistent_memory.memory_ids)
        root_task.persistent_memory_context_summary = persistent_memory.summary_text
        root_task.persistent_memory_context_digest = persistent_memory.summary_digest
        self.store.update_task(root_task)
        self.task_service.artifact_store.write_task_snapshot(root_task)
        return self._build_workflow_memory_state(root_task)

    @staticmethod
    def _build_workflow_memory_state(root_task: VideoTask) -> WorkflowMemoryState:
        return WorkflowMemoryState(
            root_task_id=root_task.task_id,
            pinned_memory_ids=list(root_task.selected_memory_ids),
            persistent_memory_context_summary=root_task.persistent_memory_context_summary,
            persistent_memory_context_digest=root_task.persistent_memory_context_digest,
        )
