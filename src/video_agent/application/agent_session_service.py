from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_session_models import AgentSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CreatedAgentSession:
    session_token: str
    session: AgentSession
    profile: AgentProfile
    token: AgentToken


class AgentSessionService:
    def __init__(
        self,
        *,
        authenticate_agent: Callable[[str], AgentPrincipal] | None = None,
        create_session_record: Callable[[AgentSession], AgentSession] | None = None,
        lookup_session_record: Callable[[str], AgentSession | None] | None = None,
        revoke_session_record: Callable[[str], bool] | None = None,
        touch_session_record: Callable[[str], AgentSession | None] | None = None,
    ) -> None:
        self.authenticate_agent = authenticate_agent or self._unsupported_auth
        self.create_session_record = create_session_record or (lambda record: record)
        self.lookup_session_record = lookup_session_record or (lambda session_hash: None)
        self.revoke_session_record = revoke_session_record or (lambda session_hash: False)
        self.touch_session_record = touch_session_record or (lambda session_hash: None)

    def create_session(self, plain_agent_token: str) -> CreatedAgentSession:
        principal = self.authenticate_agent(plain_agent_token)
        plain_session_token = f"esm_sess.{uuid4().hex}.{secrets.token_urlsafe(24)}"
        session = AgentSession(
            session_id=f"sess-{uuid4().hex}",
            session_hash=self.hash_session_token(plain_session_token),
            agent_id=principal.agent_id,
            token_hash=principal.token.token_hash,
        )
        persisted = self.create_session_record(session)
        return CreatedAgentSession(
            session_token=plain_session_token,
            session=persisted,
            profile=principal.profile,
            token=principal.token,
        )

    def resolve_session(self, plain_session_token: str) -> AgentSession:
        session_hash = self.hash_session_token(plain_session_token)
        session = self.lookup_session_record(session_hash)
        if session is None:
            raise ValueError("unknown agent session")
        self._require_active_session(session)

        touched = self.touch_session_record(session_hash)
        resolved = touched or session
        self._require_active_session(resolved)
        return resolved

    def revoke_session(self, plain_session_token: str) -> bool:
        return self.revoke_session_record(self.hash_session_token(plain_session_token))

    def resolve_session_id(self, plain_session_token: str) -> str:
        return self.resolve_session(plain_session_token).session_id

    @staticmethod
    def hash_session_token(plain_session_token: str) -> str:
        return hashlib.sha256(plain_session_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _unsupported_auth(_: str) -> AgentPrincipal:
        raise RuntimeError("authenticate_agent callback is required")

    @staticmethod
    def _require_active_session(session: AgentSession) -> None:
        if session.status != "active":
            raise ValueError("inactive agent session")
        if session.revoked_at is not None:
            raise ValueError("revoked agent session")
        if session.expires_at <= _utcnow():
            raise ValueError("expired agent session")
