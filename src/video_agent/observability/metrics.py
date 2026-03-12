from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricsCollector:
    counters: dict[str, int] = field(default_factory=dict)
    timings: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + value

    def record_timing(self, name: str, seconds: float) -> None:
        self.timings.setdefault(name, []).append(seconds)
