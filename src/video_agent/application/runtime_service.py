from __future__ import annotations

import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.config import Settings
from video_agent.validation.runtime_smoke import run_mathtex_smoke
from video_agent.version import get_release_metadata


class RuntimeCheckResult(BaseModel):
    command: str
    available: bool
    resolved_path: Optional[str] = None


class RuntimeFeatureStatus(BaseModel):
    checked: bool = False
    available: bool
    missing_checks: list[str] = Field(default_factory=list)
    smoke_error: Optional[str] = None


class RuntimeProviderStatus(BaseModel):
    mode: str
    configured: bool
    base_url_present: bool


class RuntimeWorkerHeartbeat(BaseModel):
    worker_id: str
    identity: str
    last_seen_at: str
    details: dict[str, object] = Field(default_factory=dict)
    stale: bool


class RuntimeWorkerStatus(BaseModel):
    embedded: bool
    workers: list[RuntimeWorkerHeartbeat] = Field(default_factory=list)


class RuntimeStorageStatus(BaseModel):
    data_dir: str
    database_path: str
    artifact_root: str


class RuntimeReleaseStatus(BaseModel):
    version: str
    channel: str


class RuntimeStatus(BaseModel):
    storage: RuntimeStorageStatus
    provider: RuntimeProviderStatus
    worker: RuntimeWorkerStatus
    release: RuntimeReleaseStatus
    checks: dict[str, RuntimeCheckResult]
    features: dict[str, RuntimeFeatureStatus]


class RuntimeService:
    CORE_CHECK_NAMES = ("manim", "ffmpeg", "ffprobe")
    MATHTEX_CHECK_NAMES = ("latex", "dvisvgm")

    def __init__(self, settings: Settings, store: SQLiteTaskStore | None = None) -> None:
        self.settings = settings
        self.store = store

    def inspect(self, run_feature_smoke: bool = False) -> RuntimeStatus:
        checks = self.inspect_checks()
        return RuntimeStatus(
            storage=RuntimeStorageStatus(
                data_dir=str(self.settings.data_dir),
                database_path=str(self.settings.database_path),
                artifact_root=str(self.settings.artifact_root),
            ),
            provider=RuntimeProviderStatus(
                mode=self.settings.llm_provider,
                configured=self._provider_configured(),
                base_url_present=bool(self.settings.llm_base_url),
            ),
            worker=RuntimeWorkerStatus(
                embedded=self.settings.run_embedded_worker,
                workers=self._load_workers(),
            ),
            release=RuntimeReleaseStatus(
                version=get_release_metadata()["version"],
                channel=self.settings.release_channel,
            ),
            checks=checks,
            features={
                "mathtex": self.inspect_mathtex_feature(checks, run_smoke=run_feature_smoke),
            },
        )

    def inspect_checks(self) -> dict[str, RuntimeCheckResult]:
        return {
            "manim": self._check_command(self.settings.manim_command),
            "ffmpeg": self._check_command(self.settings.ffmpeg_command),
            "ffprobe": self._check_command(self.settings.ffprobe_command),
            "latex": self._check_command(self.settings.latex_command),
            "dvisvgm": self._check_command(self.settings.dvisvgm_command),
        }

    def inspect_mathtex_feature(
        self,
        checks: dict[str, RuntimeCheckResult] | None = None,
        *,
        run_smoke: bool = False,
    ) -> RuntimeFeatureStatus:
        effective_checks = checks or self.inspect_checks()
        missing = [name for name in self.MATHTEX_CHECK_NAMES if not effective_checks[name].available]
        if missing:
            return RuntimeFeatureStatus(
                checked=False,
                available=False,
                missing_checks=missing,
                smoke_error=None,
            )
        if not run_smoke:
            return RuntimeFeatureStatus(
                checked=False,
                available=True,
                missing_checks=[],
                smoke_error=None,
            )

        smoke_result = run_mathtex_smoke(
            work_dir=self.settings.data_dir / ".runtime-smoke" / "mathtex",
            latex_command=self.settings.latex_command,
            dvisvgm_command=self.settings.dvisvgm_command,
        )
        return RuntimeFeatureStatus(
            checked=smoke_result.checked,
            available=smoke_result.available,
            missing_checks=[],
            smoke_error=smoke_result.error,
        )

    def _load_workers(self) -> list[RuntimeWorkerHeartbeat]:
        if self.store is None:
            return []

        now = datetime.now(timezone.utc)
        workers: list[RuntimeWorkerHeartbeat] = []
        for item in self.store.list_worker_heartbeats():
            last_seen = datetime.fromisoformat(item["last_seen_at"])
            stale = (now - last_seen).total_seconds() > self.settings.worker_stale_after_seconds
            workers.append(
                RuntimeWorkerHeartbeat(
                    worker_id=item["worker_id"],
                    identity=str(item["details"].get("worker_identity", item["worker_id"])),
                    last_seen_at=item["last_seen_at"],
                    details=item["details"],
                    stale=stale,
                )
            )
        return workers

    def _provider_configured(self) -> bool:
        if self.settings.llm_provider == "stub":
            return True
        if self.settings.llm_provider == "openai_compatible":
            return bool(self.settings.llm_base_url and self.settings.llm_api_key)
        return False

    def _check_command(self, command: str) -> RuntimeCheckResult:
        executable = self._extract_executable(command)
        resolved_path = None
        if executable is not None:
            path = Path(executable)
            if path.is_absolute():
                if path.exists():
                    resolved_path = str(path)
            else:
                resolved_path = shutil.which(executable)
        return RuntimeCheckResult(
            command=command,
            available=resolved_path is not None,
            resolved_path=resolved_path,
        )

    @staticmethod
    def _extract_executable(command: str) -> Optional[str]:
        parts = shlex.split(command)
        if not parts:
            return None
        return parts[0]
