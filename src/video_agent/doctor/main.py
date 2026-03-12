from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from video_agent.application.runtime_service import RuntimeService
from video_agent.server.main import build_settings
from video_agent.version import get_release_metadata



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run runtime diagnostics for easy-manim")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict-provider", action="store_true")
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim {metadata['version']} ({metadata['channel']})")
    return parser



def _status_ok(payload: dict[str, object], strict_provider: bool) -> bool:
    checks = payload["checks"]
    binaries_ok = all(item["available"] for item in checks.values())
    provider = payload["provider"]
    provider_required = strict_provider or provider["mode"] != "stub"
    provider_ok = provider["configured"] if provider_required else True
    return binaries_ok and provider_ok



def _render_text(payload: dict[str, object]) -> str:
    lines = [
        "easy-manim runtime diagnostics",
        f"provider: {payload['provider']['mode']} (configured={payload['provider']['configured']})",
        f"data_dir: {payload['storage']['data_dir']}",
        f"database_path: {payload['storage']['database_path']}",
        f"artifact_root: {payload['storage']['artifact_root']}",
        f"embedded_worker: {payload['worker']['embedded']}",
        f"release: {payload['release']['version']} ({payload['release']['channel']})",
        "checks:",
    ]
    for name, item in payload["checks"].items():
        resolved = item["resolved_path"] or "missing"
        lines.append(f"- {name}: available={item['available']} resolved={resolved}")
    return "\n".join(lines)



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir)
    payload = RuntimeService(settings=settings).inspect().model_dump(mode="json")
    ok = _status_ok(payload, strict_provider=args.strict_provider)

    if args.json:
        print(json.dumps(payload))
    else:
        print(_render_text(payload))

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
