from __future__ import annotations

from typing import Any

from video_agent.application.persistent_memory_service import PersistentMemoryContext
from video_agent.domain.models import VideoTask


def persistent_memory_ids_from_task(task: VideoTask) -> list[str]:
    persistent = _persistent_memory_section(task)
    memory_ids = persistent.get("memory_ids")
    normalized = _normalize_string_list(memory_ids)
    if normalized:
        return normalized
    return _normalize_string_list(task.selected_memory_ids)


def session_memory_summary_from_task(task: VideoTask) -> str | None:
    session = _session_memory_section(task)
    summary_text = str(session.get("summary_text") or "").strip()
    if summary_text:
        return summary_text
    fallback = str(task.memory_context_summary or "").strip()
    return fallback or None


def session_memory_digest_from_task(task: VideoTask) -> str | None:
    session = _session_memory_section(task)
    summary_digest = str(session.get("summary_digest") or "").strip()
    if summary_digest:
        return summary_digest
    fallback = str(task.memory_context_digest or "").strip()
    return fallback or None


def persistent_memory_summary_from_task(task: VideoTask) -> str | None:
    persistent = _persistent_memory_section(task)
    summary_text = str(persistent.get("summary_text") or "").strip()
    if summary_text:
        return summary_text
    for item in persistent_memory_items_from_task(task):
        text = str(item.get("summary_text") or "").strip()
        if text:
            return text
    fallback = str(task.persistent_memory_context_summary or "").strip()
    return fallback or None


def persistent_memory_digest_from_task(task: VideoTask) -> str | None:
    persistent = _persistent_memory_section(task)
    summary_digest = str(persistent.get("summary_digest") or "").strip()
    if summary_digest:
        return summary_digest
    for item in persistent_memory_items_from_task(task):
        digest = str(item.get("summary_digest") or "").strip()
        if digest:
            return digest
    fallback = str(task.persistent_memory_context_digest or "").strip()
    return fallback or None


def persistent_memory_items_from_task(task: VideoTask) -> list[dict[str, Any]]:
    persistent = _persistent_memory_section(task)
    items = persistent.get("items")
    if isinstance(items, list):
        normalized_items = [dict(item) for item in items if isinstance(item, dict)]
        if normalized_items:
            return normalized_items

    memory_ids = _normalize_string_list(persistent.get("memory_ids"))
    summary_text = str(persistent.get("summary_text") or "").strip()
    summary_digest = str(persistent.get("summary_digest") or "").strip()
    if not memory_ids:
        memory_ids = _normalize_string_list(task.selected_memory_ids)
    if not summary_text:
        summary_text = str(task.persistent_memory_context_summary or "").strip()
    if not summary_digest:
        summary_digest = str(task.persistent_memory_context_digest or "").strip()
    if not memory_ids or not summary_text:
        return []

    return [
        {
            "memory_id": memory_id,
            "summary_text": summary_text,
            "summary_digest": summary_digest or None,
            "lineage_refs": [],
            "enhancement": {},
        }
        for memory_id in memory_ids
    ]


def apply_persistent_memory_context_to_task(task: VideoTask, persistent_memory: PersistentMemoryContext | None) -> None:
    if persistent_memory is None:
        return

    memory_ids = list(persistent_memory.memory_ids)
    summary_text = str(persistent_memory.summary_text or "").strip() or None
    summary_digest = str(persistent_memory.summary_digest or "").strip() or None
    items = _normalize_persistent_memory_items(persistent_memory)

    _apply_task_memory_section(
        task,
        "persistent",
        {
            "memory_ids": memory_ids,
            "summary_text": summary_text,
            "summary_digest": summary_digest,
            "items": items,
        },
    )
    task.selected_memory_ids = memory_ids
    task.persistent_memory_context_summary = summary_text
    task.persistent_memory_context_digest = summary_digest


def _persistent_memory_section(task: VideoTask) -> dict[str, Any]:
    task_memory_context = task.task_memory_context if isinstance(task.task_memory_context, dict) else {}
    persistent = task_memory_context.get("persistent")
    if not isinstance(persistent, dict):
        return {}
    return persistent


def _session_memory_section(task: VideoTask) -> dict[str, Any]:
    task_memory_context = task.task_memory_context if isinstance(task.task_memory_context, dict) else {}
    session = task_memory_context.get("session")
    if not isinstance(session, dict):
        return {}
    return session


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            normalized.append(text)
    return list(dict.fromkeys(normalized))


def _apply_task_memory_section(task: VideoTask, section: str, payload: dict[str, Any]) -> None:
    context = dict(task.task_memory_context or {})
    context[section] = payload
    task.task_memory_context = context


def _normalize_persistent_memory_items(persistent_memory: PersistentMemoryContext) -> list[dict[str, Any]]:
    if persistent_memory.items:
        return [dict(item) for item in persistent_memory.items]
    if not persistent_memory.memory_ids or not persistent_memory.summary_text:
        return []
    return [
        {
            "memory_id": memory_id,
            "summary_text": persistent_memory.summary_text,
            "summary_digest": persistent_memory.summary_digest,
            "lineage_refs": [],
            "enhancement": {},
        }
        for memory_id in persistent_memory.memory_ids
    ]
