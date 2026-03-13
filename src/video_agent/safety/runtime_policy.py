from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None


class RuntimePolicyError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class RuntimePolicy:
    def __init__(
        self,
        work_root: Path,
        render_timeout_seconds: int = 300,
        *,
        network_disabled: bool = False,
        process_limit: int | None = None,
        memory_limit_mb: int | None = None,
        temp_root: Path | None = None,
    ) -> None:
        self.work_root = Path(work_root).resolve()
        self.render_timeout_seconds = render_timeout_seconds
        self.network_disabled = network_disabled
        self.process_limit = process_limit if process_limit and process_limit > 0 else None
        self.memory_limit_mb = memory_limit_mb if memory_limit_mb and memory_limit_mb > 0 else None
        self.temp_root = Path(temp_root or (self.work_root / ".sandbox" / "tmp")).resolve()

    def is_allowed_write(self, path: Path) -> bool:
        target = Path(path).resolve()
        try:
            target.relative_to(self.work_root)
            return True
        except ValueError:
            return False

    def prepare_render_environment(
        self,
        base_env: dict[str, str] | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, str]:
        effective_env = dict(os.environ)
        effective_env.update(base_env or {})
        effective_env.update(env or {})
        effective_env["TMPDIR"] = str(self.ensure_temp_root())
        if self.network_disabled:
            for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
                effective_env[key] = ""
            effective_env["NO_PROXY"] = "*"
            effective_env["no_proxy"] = "*"
        return effective_env

    def build_preexec_fn(self) -> Callable[[], None] | None:
        if resource is None:
            return None
        if self.memory_limit_mb is None:
            return None

        def _apply_limits() -> None:
            if self.memory_limit_mb is not None and hasattr(resource, "RLIMIT_AS"):
                limit_bytes = self.memory_limit_mb * 1024 * 1024
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
                except (OSError, ValueError):
                    pass

        return _apply_limits

    def ensure_temp_root(self) -> Path:
        if not self.is_allowed_write(self.temp_root):
            raise RuntimePolicyError(
                code="sandbox_temp_root_outside_work_root",
                message=f"Sandbox temp root must stay inside work root: {self.temp_root}",
                details={"temp_root": str(self.temp_root), "work_root": str(self.work_root)},
            )
        self.temp_root.mkdir(parents=True, exist_ok=True)
        return self.temp_root

    def describe(self) -> dict[str, Any]:
        resource_limits_supported = resource is not None and hasattr(resource, "setrlimit")
        return {
            "network_disabled": self.network_disabled,
            "temp_root": str(self.temp_root),
            "temp_root_allowed": self.is_allowed_write(self.temp_root),
            "process_limit": self.process_limit,
            "memory_limit_mb": self.memory_limit_mb,
            "resource_limits_supported": resource_limits_supported,
        }
