from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


GatewaySourceKind = Literal[
    "direct_message",
    "group_chat",
    "cron",
    "webhook",
    "mcp_transport",
    "http_control",
]


class GatewayRoute(BaseModel):
    source_kind: GatewaySourceKind
    source_id: str | None = None
    channel: str | None = None
    room_id: str | None = None
    peer_id: str | None = None
    job_id: str | None = None
    agent_id: str | None = None


class GatewaySessionPolicy(BaseModel):
    dm_scope: Literal["main", "per_peer"] = "main"
    daily_reset_hour_local: int = 4
    idle_reset_minutes: int | None = None

    @model_validator(mode="after")
    def normalize(self) -> "GatewaySessionPolicy":
        self.daily_reset_hour_local = min(max(self.daily_reset_hour_local, 0), 23)
        if self.idle_reset_minutes is not None and self.idle_reset_minutes <= 0:
            self.idle_reset_minutes = None
        return self


class GatewaySessionRecord(BaseModel):
    session_id: str
    route_key: str
    source_kind: GatewaySourceKind
    agent_id: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    last_active_at: datetime = Field(default_factory=_utcnow)


class GatewaySessionResolution(BaseModel):
    session_id: str
    created: bool
    reset_reason: str | None = None
    record: GatewaySessionRecord


class GatewaySessionService:
    def __init__(
        self,
        *,
        policy: GatewaySessionPolicy | None = None,
    ) -> None:
        self.policy = policy or GatewaySessionPolicy()
        self._records_by_route_key: dict[str, GatewaySessionRecord] = {}

    def resolve(
        self,
        route: GatewayRoute,
        *,
        now: datetime | None = None,
    ) -> GatewaySessionResolution:
        current_time = now or _utcnow()
        route_key = self._route_key(route)

        if route.source_kind == "cron":
            record = self._new_record(route=route, route_key=route_key, now=current_time)
            self._records_by_route_key[route_key] = record
            return GatewaySessionResolution(
                session_id=record.session_id,
                created=True,
                reset_reason="fresh_run",
                record=record,
            )

        existing = self._records_by_route_key.get(route_key)
        reset_reason: str | None = None
        if existing is None:
            record = self._new_record(route=route, route_key=route_key, now=current_time)
            created = True
        elif self._requires_daily_reset(existing, current_time):
            record = self._new_record(route=route, route_key=route_key, now=current_time)
            created = True
            reset_reason = "daily_reset"
        elif self._requires_idle_reset(existing, current_time):
            record = self._new_record(route=route, route_key=route_key, now=current_time)
            created = True
            reset_reason = "idle_reset"
        else:
            record = existing.model_copy(update={"last_active_at": current_time}, deep=True)
            created = False

        self._records_by_route_key[route_key] = record
        return GatewaySessionResolution(
            session_id=record.session_id,
            created=created,
            reset_reason=reset_reason,
            record=record,
        )

    def _route_key(self, route: GatewayRoute) -> str:
        agent_scope = route.agent_id or "default"
        prefix = f"agent:{agent_scope}"
        if route.source_kind == "direct_message":
            if self.policy.dm_scope == "main":
                return f"{prefix}:dm:main"
            identity = route.peer_id or route.source_id
            if not identity:
                raise ValueError("direct_message route requires peer_id or source_id")
            return f"{prefix}:dm:peer:{identity}"
        if route.source_kind == "group_chat":
            room_identity = route.room_id or route.source_id
            if not room_identity:
                raise ValueError("group_chat route requires room_id or source_id")
            channel = route.channel or "group"
            return f"{prefix}:group:{channel}:{room_identity}"
        if route.source_kind == "cron":
            job_identity = route.job_id or route.source_id or "default"
            return f"{prefix}:cron:{job_identity}"
        if route.source_kind == "webhook":
            identity = route.source_id
            if not identity:
                raise ValueError("webhook route requires source_id")
            channel = route.channel or "webhook"
            return f"{prefix}:webhook:{channel}:{identity}"
        if route.source_kind in {"mcp_transport", "http_control"}:
            identity = route.source_id
            if not identity:
                raise ValueError(f"{route.source_kind} route requires source_id")
            return f"{prefix}:{route.source_kind}:{identity}"
        raise ValueError(f"Unsupported source_kind: {route.source_kind}")

    def _new_record(
        self,
        *,
        route: GatewayRoute,
        route_key: str,
        now: datetime,
    ) -> GatewaySessionRecord:
        return GatewaySessionRecord(
            session_id=f"gw-sess-{uuid4().hex}",
            route_key=route_key,
            source_kind=route.source_kind,
            agent_id=route.agent_id,
            created_at=now,
            last_active_at=now,
        )

    def _requires_daily_reset(self, record: GatewaySessionRecord, now: datetime) -> bool:
        reset_boundary = now.replace(
            hour=self.policy.daily_reset_hour_local,
            minute=0,
            second=0,
            microsecond=0,
        )
        if now < reset_boundary:
            reset_boundary -= timedelta(days=1)
        return record.created_at < reset_boundary <= now

    def _requires_idle_reset(self, record: GatewaySessionRecord, now: datetime) -> bool:
        if self.policy.idle_reset_minutes is None:
            return False
        return now - record.last_active_at >= timedelta(minutes=self.policy.idle_reset_minutes)
