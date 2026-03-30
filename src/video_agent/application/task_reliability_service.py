from __future__ import annotations

from typing import Any

from video_agent.application.case_reliability_service import CaseReliabilityService


class TaskReliabilityService:
    def __init__(
        self,
        *,
        case_reliability_service: CaseReliabilityService | None = None,
        **kwargs: Any,
    ) -> None:
        self.case_reliability_service = case_reliability_service or CaseReliabilityService(**kwargs)

    def reconcile_startup(self) -> dict[str, int]:
        return self.case_reliability_service.reconcile_startup()

    def sweep_watchdog(self) -> dict[str, int]:
        return self.case_reliability_service.sweep_watchdog()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.case_reliability_service, name)
