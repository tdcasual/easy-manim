import pytest

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.agent_session_service import AgentSessionService
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_session_models import AgentSession


def test_create_session_returns_plaintext_secret_and_persisted_record() -> None:
    created_records: list[AgentSession] = []

    service = AgentSessionService(
        authenticate_agent=lambda token: AgentPrincipal(
            agent_id="agent-a",
            profile=AgentProfile(agent_id="agent-a", name="Agent A"),
            token=AgentToken(token_hash="token-hash", agent_id="agent-a"),
        ),
        create_session_record=lambda record: created_records.append(record) or record,
    )

    payload = service.create_session("plain-agent-token")

    assert payload.session_token.startswith("esm_sess.")
    assert created_records[0].agent_id == "agent-a"
    assert created_records[0].session_hash != payload.session_token


def test_resolve_session_returns_persisted_record_and_touches_last_seen() -> None:
    touched_hashes: list[str] = []
    session_hash = AgentSessionService.hash_session_token("esm_sess.plain")
    persisted = AgentSession(session_id="sess-1", session_hash=session_hash, agent_id="agent-a")
    service = AgentSessionService(
        lookup_session_record=lambda lookup_hash: persisted if lookup_hash == session_hash else None,
        touch_session_record=lambda session_hash: touched_hashes.append(session_hash) or persisted,
    )

    resolved = service.resolve_session("esm_sess.plain")

    assert resolved.agent_id == "agent-a"
    assert touched_hashes == [service.hash_session_token("esm_sess.plain")]


def test_revoke_session_hashes_token_before_revoking() -> None:
    revoked_hashes: list[str] = []
    service = AgentSessionService(
        revoke_session_record=lambda session_hash: revoked_hashes.append(session_hash) or True,
    )

    assert service.revoke_session("esm_sess.plain") is True
    assert revoked_hashes == [service.hash_session_token("esm_sess.plain")]


def test_resolve_session_rejects_unknown_record() -> None:
    service = AgentSessionService()

    with pytest.raises(ValueError, match="unknown agent session"):
        service.resolve_session("esm_sess.plain")
