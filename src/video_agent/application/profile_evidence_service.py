from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ProfileEvidenceBundle:
    patch: dict[str, Any]
    sources: list[dict[str, Any]]
    supporting_evidence_counts: dict[str, int]
    field_support: dict[str, dict[str, Any]]
    conflicts: list[dict[str, Any]]

    def has_strong_field_support(self, *, min_support_per_field: int = 2) -> bool:
        if not self.patch:
            return False
        if min_support_per_field <= 1:
            return True
        return max(self.supporting_evidence_counts.values(), default=0) >= min_support_per_field


class ProfileEvidenceService:
    def build_bundle(self, texts: list[tuple[str, dict[str, Any]]]) -> ProfileEvidenceBundle:
        sources: list[dict[str, Any]] = []
        evidence_by_field: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        value_lookup: dict[tuple[str, str], Any] = {}

        for summary_text, provenance in texts:
            field_evidence = self.extract(summary_text, provenance)
            if not field_evidence:
                continue
            sources.append({**provenance, "summary_text": summary_text})
            for item in field_evidence:
                field_path = str(item["field"])
                value = item["value"]
                value_key = self._value_key(value)
                evidence_by_field[field_path][value_key].append(item)
                value_lookup[(field_path, value_key)] = value

        patch, supporting_evidence_counts, field_support, conflicts = self.aggregate(
            evidence_by_field=evidence_by_field,
            value_lookup=value_lookup,
        )
        return ProfileEvidenceBundle(
            patch=patch,
            sources=sources,
            supporting_evidence_counts=supporting_evidence_counts,
            field_support=field_support,
            conflicts=conflicts,
        )

    @staticmethod
    def extract(summary_text: str, provenance: dict[str, Any]) -> list[dict[str, Any]]:
        normalized = summary_text.lower()
        evidence: list[dict[str, Any]] = []

        def add(field: str, value: Any) -> None:
            evidence.append(
                {
                    "field": field,
                    "value": value,
                    "source": provenance.get("source"),
                    "memory_id": provenance.get("memory_id"),
                    "session_id": provenance.get("session_id"),
                }
            )

        if re.search(r"\bteaching(?:\s+tone)?\b", normalized):
            add("style_hints.tone", "teaching")
        elif re.search(r"\bpatient(?:\s+tone)?\b", normalized):
            add("style_hints.tone", "patient")
        elif re.search(r"\bdirect(?:\s+tone)?\b", normalized):
            add("style_hints.tone", "direct")

        if re.search(r"\bsteady(?:\s+(?:pacing|pace))?\b", normalized):
            add("style_hints.pace", "steady")
        elif re.search(r"\bbrisk(?:\s+(?:pacing|pace))?\b", normalized):
            add("style_hints.pace", "brisk")

        resolution_match = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", normalized)
        if resolution_match:
            add("output_profile.pixel_width", int(resolution_match.group(1)))
            add("output_profile.pixel_height", int(resolution_match.group(2)))

        if re.search(r"\bstrict validation\b", normalized) or re.search(r"\bstrictly validate\b", normalized):
            add("validation_profile.strict", True)

        return evidence

    @classmethod
    def aggregate(
        cls,
        *,
        evidence_by_field: dict[str, dict[str, list[dict[str, Any]]]],
        value_lookup: dict[tuple[str, str], Any],
    ) -> tuple[dict[str, Any], dict[str, int], dict[str, dict[str, Any]], list[dict[str, Any]]]:
        patch: dict[str, Any] = {}
        supporting_evidence_counts: dict[str, int] = {}
        field_support: dict[str, dict[str, Any]] = {}
        conflicts: list[dict[str, Any]] = []

        for field_path in sorted(evidence_by_field):
            options = evidence_by_field[field_path]
            if len(options) > 1:
                conflicts.append(
                    {
                        "field": field_path,
                        "values": [
                            {
                                "value": value_lookup[(field_path, value_key)],
                                "count": len(items),
                                "source_type_counts": cls._source_type_counts(items),
                            }
                            for value_key, items in sorted(
                                options.items(),
                                key=lambda option: (-len(option[1]), option[0]),
                            )
                        ],
                    }
                )
                continue

            value_key, items = next(iter(options.items()))
            cls._assign_patch_value(patch, field_path, value_lookup[(field_path, value_key)])
            support_count = len(items)
            source_type_counts = cls._source_type_counts(items)
            supporting_evidence_counts[field_path] = support_count
            field_support[field_path] = {
                "support_count": support_count,
                "source_type_counts": source_type_counts,
                "distinct_session_count": len({str(item.get("session_id")) for item in items if item.get("session_id")}),
                "distinct_memory_count": len({str(item.get("memory_id")) for item in items if item.get("memory_id")}),
                "confidence": cls._field_confidence(support_count=support_count, source_type_counts=source_type_counts),
            }

        return patch, supporting_evidence_counts, field_support, conflicts

    @staticmethod
    def _assign_patch_value(patch: dict[str, Any], field_path: str, value: Any) -> None:
        current = patch
        parts = field_path.split(".")
        for key in parts[:-1]:
            current = current.setdefault(key, {})
        current[parts[-1]] = value

    @staticmethod
    def _field_confidence(*, support_count: int, source_type_counts: dict[str, int]) -> float:
        support_strength = min(support_count, 3) / 3 if support_count else 0.0
        source_diversity = min(len(source_type_counts), 2) / 2 if source_type_counts else 0.0
        confidence = 0.55 + support_strength * 0.25 + source_diversity * 0.20
        return round(max(0.0, min(1.0, confidence)), 4)

    @staticmethod
    def _source_type_counts(items: list[dict[str, Any]]) -> dict[str, int]:
        counts = Counter(str(item["source"]) for item in items if item.get("source"))
        return dict(counts)

    @staticmethod
    def _value_key(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
