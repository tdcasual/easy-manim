from __future__ import annotations

from datetime import datetime, timedelta, timezone

from video_agent.openclaw.gateway_sessions import (
    GatewayRoute,
    GatewaySessionPolicy,
    GatewaySessionService,
)


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def test_direct_message_routes_to_shared_session_by_default() -> None:
    service = GatewaySessionService(policy=GatewaySessionPolicy())

    first = service.resolve(
        GatewayRoute(
            source_kind="direct_message",
            source_id="message-a",
            peer_id="alice",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 3, 0),
    )
    second = service.resolve(
        GatewayRoute(
            source_kind="direct_message",
            source_id="message-b",
            peer_id="bob",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 3, 5),
    )

    assert first.session_id == second.session_id
    assert second.created is False


def test_direct_message_can_isolate_per_peer() -> None:
    service = GatewaySessionService(
        policy=GatewaySessionPolicy(dm_scope="per_peer"),
    )

    first = service.resolve(
        GatewayRoute(
            source_kind="direct_message",
            source_id="message-a",
            peer_id="alice",
            agent_id="main",
        ),
    )
    second = service.resolve(
        GatewayRoute(
            source_kind="direct_message",
            source_id="message-b",
            peer_id="bob",
            agent_id="main",
        ),
    )

    assert first.session_id != second.session_id


def test_group_chat_isolated_per_room() -> None:
    service = GatewaySessionService(policy=GatewaySessionPolicy())

    first = service.resolve(
        GatewayRoute(
            source_kind="group_chat",
            channel="discord",
            room_id="room-a",
            agent_id="main",
        ),
    )
    second = service.resolve(
        GatewayRoute(
            source_kind="group_chat",
            channel="discord",
            room_id="room-b",
            agent_id="main",
        ),
    )

    assert first.session_id != second.session_id


def test_cron_jobs_always_create_fresh_sessions() -> None:
    service = GatewaySessionService(policy=GatewaySessionPolicy())

    first = service.resolve(
        GatewayRoute(
            source_kind="cron",
            job_id="daily-summary",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 9, 0),
    )
    second = service.resolve(
        GatewayRoute(
            source_kind="cron",
            job_id="daily-summary",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 9, 1),
    )

    assert first.session_id != second.session_id
    assert second.created is True
    assert second.reset_reason == "fresh_run"


def test_daily_reset_rotates_existing_session() -> None:
    service = GatewaySessionService(
        policy=GatewaySessionPolicy(daily_reset_hour_local=4),
    )

    first = service.resolve(
        GatewayRoute(
            source_kind="direct_message",
            source_id="message-a",
            peer_id="alice",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 3, 59),
    )
    rotated = service.resolve(
        GatewayRoute(
            source_kind="direct_message",
            source_id="message-b",
            peer_id="alice",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 4, 1),
    )

    assert first.session_id != rotated.session_id
    assert rotated.created is True
    assert rotated.reset_reason == "daily_reset"


def test_idle_reset_rotates_inactive_session() -> None:
    service = GatewaySessionService(
        policy=GatewaySessionPolicy(idle_reset_minutes=10),
    )

    first = service.resolve(
        GatewayRoute(
            source_kind="group_chat",
            channel="slack",
            room_id="design-review",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 10, 0),
    )
    rotated = service.resolve(
        GatewayRoute(
            source_kind="group_chat",
            channel="slack",
            room_id="design-review",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 10, 11),
    )

    assert first.session_id != rotated.session_id
    assert rotated.reset_reason == "idle_reset"


def test_recent_activity_reuses_existing_session_before_idle_cutoff() -> None:
    service = GatewaySessionService(
        policy=GatewaySessionPolicy(idle_reset_minutes=10),
    )

    first = service.resolve(
        GatewayRoute(
            source_kind="mcp_transport",
            source_id="ctx-1",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 10, 0),
    )
    reused = service.resolve(
        GatewayRoute(
            source_kind="mcp_transport",
            source_id="ctx-1",
            agent_id="main",
        ),
        now=_utc(2026, 4, 7, 10, 9),
    )

    assert first.session_id == reused.session_id
    assert reused.created is False
    assert reused.reset_reason is None
    assert reused.record.last_active_at == _utc(2026, 4, 7, 10, 9)
