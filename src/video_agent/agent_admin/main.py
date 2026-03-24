from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path
from typing import Any

from video_agent.adapters.storage.sqlite_bootstrap import DatabaseBootstrapRequiredError, SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.main import build_settings
from video_agent.version import get_release_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage easy-manim agent profiles and tokens")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    metadata = get_release_metadata()
    parser.add_argument("--version", action="version", version=f"easy-manim {metadata['version']} ({metadata['channel']})")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_profile = subparsers.add_parser("create-profile", help="Create or update an agent profile")
    create_profile.add_argument("--agent-id", required=True)
    create_profile.add_argument("--name", required=True)
    create_profile.add_argument("--profile-json", default="{}")
    create_profile.add_argument("--policy-json", default="{}")

    issue_token = subparsers.add_parser("issue-token", help="Issue a new agent token")
    issue_token.add_argument("--agent-id", required=True)
    issue_token.add_argument("--scopes-json", default="{}")
    issue_token.add_argument("--override-json", default="{}")

    disable_token = subparsers.add_parser("disable-token", help="Disable an issued token by hash")
    disable_token.add_argument("--token-hash", required=True)

    inspect_profile = subparsers.add_parser("inspect-profile", help="Inspect an agent profile and issued tokens")
    inspect_profile.add_argument("--agent-id", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        store = _build_store(args.data_dir)
    except DatabaseBootstrapRequiredError as exc:
        raise SystemExit(str(exc)) from exc

    if args.command == "create-profile":
        profile = AgentProfile(
            agent_id=args.agent_id,
            name=args.name,
            profile_json=_parse_json(args.profile_json, label="profile-json"),
            policy_json=_parse_json(args.policy_json, label="policy-json"),
        )
        store.upsert_agent_profile(profile)
        print(
            json.dumps(
                {
                    "agent_id": profile.agent_id,
                    "name": profile.name,
                    "status": profile.status,
                    "profile_json": profile.profile_json,
                    "policy_json": profile.policy_json,
                }
            )
        )
        return

    if args.command == "issue-token":
        profile = store.get_agent_profile(args.agent_id)
        if profile is None:
            raise SystemExit(f"Unknown agent profile: {args.agent_id}")
        plaintext_token = _generate_agent_token(args.agent_id)
        token_hash = hash_agent_token(plaintext_token)
        token = AgentToken(
            token_hash=token_hash,
            agent_id=args.agent_id,
            scopes_json=_parse_json(args.scopes_json, label="scopes-json"),
            override_json=_parse_json(args.override_json, label="override-json"),
        )
        store.issue_agent_token(token)
        print(
            json.dumps(
                {
                    "agent_id": args.agent_id,
                    "agent_token": plaintext_token,
                    "token_hash": token_hash,
                    "status": token.status,
                    "scopes_json": token.scopes_json,
                }
            )
        )
        return

    if args.command == "disable-token":
        if not store.disable_agent_token(args.token_hash):
            raise SystemExit(f"Unknown token hash: {args.token_hash}")
        print(json.dumps({"token_hash": args.token_hash, "status": "disabled"}))
        return

    if args.command == "inspect-profile":
        profile = store.get_agent_profile(args.agent_id)
        if profile is None:
            raise SystemExit(f"Unknown agent profile: {args.agent_id}")
        tokens = [token.model_dump(mode="json") for token in store.list_agent_tokens(args.agent_id)]
        print(json.dumps({"profile": profile.model_dump(mode="json"), "tokens": tokens}))
        return

    raise SystemExit(f"Unsupported command: {args.command}")


def _build_store(data_dir: Path) -> SQLiteTaskStore:
    settings = build_settings(data_dir)
    SQLiteBootstrapper(settings.database_path).require_bootstrapped(data_dir=settings.data_dir)
    return SQLiteTaskStore(settings.database_path)


def _parse_json(raw: str, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for {label}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit(f"{label} must decode to a JSON object")
    return parsed


def _generate_agent_token(agent_id: str) -> str:
    return f"easy-manim.{agent_id}.{secrets.token_urlsafe(24)}"


if __name__ == "__main__":
    main()
