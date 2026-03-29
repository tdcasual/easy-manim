from __future__ import annotations

import re
from typing import Any, Callable

from video_agent.application.preference_resolver import resolve_effective_request_config
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_profile_suggestion_models import AgentProfileSuggestion


class AgentProfileSuggestionService:
    def __init__(
        self,
        *,
        list_memories: Callable[[str], list[AgentMemoryRecord]],
        list_recent_session_summaries: Callable[[str], list[dict[str, Any]]],
        build_scorecard: Callable[[str], dict[str, object]],
        create_suggestion: Callable[[AgentProfileSuggestion], AgentProfileSuggestion],
    ) -> None:
        self._list_memories = list_memories
        self._list_recent_session_summaries = list_recent_session_summaries
        self._build_scorecard = build_scorecard
        self._create_suggestion = create_suggestion

    def generate_suggestions(self, agent_id: str, *, profile_version: int | None = None) -> list[AgentProfileSuggestion]:
        scorecard = self._build_scorecard(agent_id)
        texts: list[tuple[str, dict[str, Any]]] = []
        for record in self._list_memories(agent_id):
            if record.status != "active" or not record.summary_text.strip():
                continue
            texts.append(
                (
                    record.summary_text,
                    {
                        "source": "memory",
                        "memory_id": record.memory_id,
                        "session_id": record.source_session_id,
                    },
                )
            )
        for summary in self._list_recent_session_summaries(agent_id):
            summary_text = str(summary.get("summary_text") or "").strip()
            if not summary_text:
                continue
            texts.append(
                (
                    summary_text,
                    {
                        "source": "session_summary",
                        "session_id": summary.get("session_id"),
                    },
                )
            )

        suggestion = self._suggestion_from_texts(
            agent_id=agent_id,
            texts=texts,
            scorecard=scorecard,
            profile_version=profile_version,
        )
        if suggestion is None:
            return []
        return [self._create_suggestion(suggestion)]

    def create_suggestion_from_summary(
        self,
        agent_id: str,
        *,
        summary_text: str,
        session_id: str | None = None,
        memory_id: str | None = None,
        profile_version: int | None = None,
        source: str = "preference_summary",
    ) -> AgentProfileSuggestion | None:
        suggestion = self._suggestion_from_texts(
            agent_id=agent_id,
            texts=[
                (
                    summary_text,
                    {
                        "source": source,
                        "session_id": session_id,
                        "memory_id": memory_id,
                    },
                )
            ],
            scorecard=self._build_scorecard(agent_id),
            profile_version=profile_version,
        )
        if suggestion is None:
            return None
        return self._create_suggestion(suggestion)

    def _suggestion_from_texts(
        self,
        *,
        agent_id: str,
        texts: list[tuple[str, dict[str, Any]]],
        scorecard: dict[str, object],
        profile_version: int | None,
    ) -> AgentProfileSuggestion | None:
        combined_patch: dict[str, Any] = {}
        sources: list[dict[str, Any]] = []
        for summary_text, provenance in texts:
            patch = self._patch_from_text(summary_text)
            if not patch:
                continue
            combined_patch = resolve_effective_request_config(
                profile_json=combined_patch,
                request_overrides=patch,
            )
            sources.append(
                {
                    **provenance,
                    "summary_text": summary_text,
                }
            )

        completed_count = int(scorecard.get("completed_count", 0) or 0)
        median_quality_score = self._scorecard_quality_metric(scorecard)
        if not combined_patch or completed_count <= 0 or median_quality_score <= 0.0:
            return None

        return AgentProfileSuggestion(
            agent_id=agent_id,
            patch_json=combined_patch,
            rationale_json={
                "sources": sources,
                "scorecard": {
                    "completed_count": completed_count,
                    "median_quality_score": median_quality_score,
                },
                "profile_version": profile_version,
            },
        )

    @staticmethod
    def _scorecard_quality_metric(scorecard: dict[str, object]) -> float:
        return float(scorecard.get("quality_score", scorecard.get("median_quality_score", 0.0)) or 0.0)

    @staticmethod
    def _patch_from_text(summary_text: str) -> dict[str, Any]:
        normalized = summary_text.lower()
        patch: dict[str, Any] = {}
        style_hints: dict[str, Any] = {}
        output_profile: dict[str, Any] = {}
        validation_profile: dict[str, Any] = {}

        if "teaching tone" in normalized or "teaching" in normalized:
            style_hints["tone"] = "teaching"
        elif "patient tone" in normalized or "patient" in normalized:
            style_hints["tone"] = "patient"
        elif "direct tone" in normalized or "direct" in normalized:
            style_hints["tone"] = "direct"

        if "steady pacing" in normalized or "steady pace" in normalized or "steady" in normalized:
            style_hints["pace"] = "steady"
        elif "brisk pacing" in normalized or "brisk pace" in normalized or "brisk" in normalized:
            style_hints["pace"] = "brisk"

        resolution_match = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", normalized)
        if resolution_match:
            output_profile["pixel_width"] = int(resolution_match.group(1))
            output_profile["pixel_height"] = int(resolution_match.group(2))

        if "strict validation" in normalized or "strictly validate" in normalized:
            validation_profile["strict"] = True

        if style_hints:
            patch["style_hints"] = style_hints
        if output_profile:
            patch["output_profile"] = output_profile
        if validation_profile:
            patch["validation_profile"] = validation_profile
        return patch
