import hashlib

import pytest

from video_agent.application.agent_identity_service import AgentIdentityService
from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_identity_service_resolves_active_token_to_profile() -> None:
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: AgentProfile(agent_id=agent_id, name="Agent A"),
        token_lookup=lambda token_hash: AgentToken(token_hash=token_hash, agent_id="agent-a"),
    )

    principal = service.authenticate("plain-token")

    assert principal.agent_id == "agent-a"
    assert principal.profile.name == "Agent A"
    assert principal.token.token_hash == hashlib.sha256(b"plain-token").hexdigest()


def test_identity_service_rejects_inactive_token() -> None:
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: AgentProfile(agent_id=agent_id, name="Agent A"),
        token_lookup=lambda token_hash: AgentToken(token_hash=token_hash, agent_id="agent-a", status="disabled"),
    )

    with pytest.raises(ValueError, match="inactive agent token"):
        service.authenticate("plain-token")
