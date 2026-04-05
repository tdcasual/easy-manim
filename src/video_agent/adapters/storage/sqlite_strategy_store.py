from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from video_agent.domain.strategy_models import StrategyProfile
from video_agent.domain.strategy_models import StrategyPromotionDecision


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


class SQLiteStrategyStoreMixin:
    @staticmethod
    def _row_to_strategy_profile(row: sqlite3.Row) -> StrategyProfile:
        return StrategyProfile(
            strategy_id=row["strategy_id"],
            scope=row["scope"],
            prompt_cluster=row["prompt_cluster"],
            status=row["status"],
            params=json.loads(row["params_json"]),
            metrics=json.loads(row["metrics_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _upsert_strategy_profile_in_connection(
        self,
        connection: sqlite3.Connection,
        profile: StrategyProfile,
    ) -> StrategyProfile:
        existing = connection.execute(
            """
            SELECT strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
            FROM strategy_profiles
            WHERE strategy_id = ?
            """,
            (profile.strategy_id,),
        ).fetchone()
        profile.updated_at = _utcnow()
        if existing is not None:
            profile.created_at = datetime.fromisoformat(existing["created_at"])
        connection.execute(
            """
            INSERT INTO strategy_profiles (
                strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_id) DO UPDATE SET
                scope = excluded.scope,
                prompt_cluster = excluded.prompt_cluster,
                status = excluded.status,
                params_json = excluded.params_json,
                metrics_json = excluded.metrics_json,
                updated_at = excluded.updated_at
            """,
            (
                profile.strategy_id,
                profile.scope,
                profile.prompt_cluster,
                profile.status,
                json.dumps(profile.params),
                json.dumps(profile.metrics),
                profile.created_at.isoformat(),
                profile.updated_at.isoformat(),
            ),
        )
        return profile

    def create_strategy_profile(self, profile: StrategyProfile) -> StrategyProfile:
        with self._connect() as connection:
            return self._upsert_strategy_profile_in_connection(connection, profile)

    def get_strategy_profile(self, strategy_id: str) -> Optional[StrategyProfile]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
                FROM strategy_profiles
                WHERE strategy_id = ?
                """,
                (strategy_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_strategy_profile(row)

    def list_strategy_profiles(self, status: str | None = None) -> list[StrategyProfile]:
        query = """
            SELECT strategy_id, scope, prompt_cluster, status, params_json, metrics_json, created_at, updated_at
            FROM strategy_profiles
        """
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._row_to_strategy_profile(row) for row in rows]

    def get_active_strategy_profile(
        self,
        *,
        scope: str,
        prompt_cluster: str | None,
        exclude_strategy_id: str | None = None,
    ) -> Optional[StrategyProfile]:
        candidates = self.list_strategy_profiles(status="active")
        for profile in candidates:
            if profile.scope != scope or profile.prompt_cluster != prompt_cluster:
                continue
            if exclude_strategy_id is not None and profile.strategy_id == exclude_strategy_id:
                continue
            return profile
        return None

    def activate_strategy_profile(
        self,
        strategy_id: str,
        *,
        applied_at: str | None = None,
    ) -> tuple[StrategyProfile, StrategyProfile | None]:
        target = self.get_strategy_profile(strategy_id)
        if target is None:
            raise ValueError(f"Unknown strategy profile: {strategy_id}")
        timestamp = applied_at or _utcnow_iso()
        previous_active = self.get_active_strategy_profile(
            scope=target.scope,
            prompt_cluster=target.prompt_cluster,
            exclude_strategy_id=target.strategy_id,
        )
        target_guarded = (
            dict(target.metrics.get("guarded_rollout", {}))
            if isinstance(target.metrics.get("guarded_rollout"), dict)
            else {}
        )
        target_guarded.update(
            {
                "last_applied_at": timestamp,
                "rollback_target_strategy_id": None if previous_active is None else previous_active.strategy_id,
                "rollback_armed": previous_active is not None,
            }
        )
        target.metrics = {
            **target.metrics,
            "guarded_rollout": target_guarded,
        }
        target.status = "active"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if previous_active is not None:
                previous_guarded = (
                    dict(previous_active.metrics.get("guarded_rollout", {}))
                    if isinstance(previous_active.metrics.get("guarded_rollout"), dict)
                    else {}
                )
                previous_guarded.update(
                    {
                        "superseded_at": timestamp,
                        "superseded_by_strategy_id": target.strategy_id,
                    }
                )
                previous_active.metrics = {
                    **previous_active.metrics,
                    "guarded_rollout": previous_guarded,
                }
                previous_active.status = "superseded"
                self._upsert_strategy_profile_in_connection(connection, previous_active)
            self._upsert_strategy_profile_in_connection(connection, target)
        return target, previous_active

    def rollback_strategy_profile(
        self,
        strategy_id: str,
        *,
        rolled_back_at: str | None = None,
    ) -> tuple[StrategyProfile, StrategyProfile]:
        target = self.get_strategy_profile(strategy_id)
        if target is None:
            raise ValueError(f"Unknown strategy profile: {strategy_id}")
        target_guarded = (
            dict(target.metrics.get("guarded_rollout", {}))
            if isinstance(target.metrics.get("guarded_rollout"), dict)
            else {}
        )
        rollback_target_strategy_id = target_guarded.get("rollback_target_strategy_id")
        if not rollback_target_strategy_id:
            raise ValueError(f"No guarded rollback target for strategy profile: {strategy_id}")
        rollback_target = self.get_strategy_profile(str(rollback_target_strategy_id))
        if rollback_target is None:
            raise ValueError(f"Unknown rollback strategy profile: {rollback_target_strategy_id}")

        timestamp = rolled_back_at or _utcnow_iso()
        target_guarded.update(
            {
                "rollback_armed": False,
                "consecutive_shadow_passes": 0,
                "last_rolled_back_at": timestamp,
            }
        )
        target.metrics = {
            **target.metrics,
            "guarded_rollout": target_guarded,
        }
        target.status = "rolled_back"

        rollback_guarded = (
            dict(rollback_target.metrics.get("guarded_rollout", {}))
            if isinstance(rollback_target.metrics.get("guarded_rollout"), dict)
            else {}
        )
        rollback_guarded.update(
            {
                "restored_at": timestamp,
                "restored_from_strategy_id": target.strategy_id,
            }
        )
        rollback_target.metrics = {
            **rollback_target.metrics,
            "guarded_rollout": rollback_guarded,
        }
        rollback_target.status = "active"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._upsert_strategy_profile_in_connection(connection, target)
            self._upsert_strategy_profile_in_connection(connection, rollback_target)
        return target, rollback_target

    def record_strategy_eval_run(
        self,
        strategy_id: str,
        *,
        baseline_summary: dict[str, Any],
        challenger_summary: dict[str, Any],
        promotion_recommended: bool,
        promotion_decision: StrategyPromotionDecision | dict[str, Any] | None = None,
    ) -> StrategyProfile:
        profile = self.get_strategy_profile(strategy_id)
        if profile is None:
            raise ValueError(f"Unknown strategy profile: {strategy_id}")
        recorded_at = _utcnow_iso()
        if promotion_decision is None:
            decision_payload = StrategyPromotionDecision(
                approved=promotion_recommended,
                reasons=[],
                deltas={},
                mode="shadow",
                applied=False,
                recorded_at=recorded_at,
            ).model_dump(mode="json")
        elif isinstance(promotion_decision, StrategyPromotionDecision):
            decision_payload = promotion_decision.model_dump(mode="json")
        else:
            decision_payload = StrategyPromotionDecision.model_validate(
                {
                    "approved": promotion_recommended,
                    "reasons": [],
                    "deltas": {},
                    "mode": "shadow",
                    "applied": False,
                    "recorded_at": recorded_at,
                    **dict(promotion_decision),
                }
            ).model_dump(mode="json")

        decision_payload["recorded_at"] = str(decision_payload.get("recorded_at") or recorded_at)
        guarded_rollout = (
            dict(profile.metrics.get("guarded_rollout", {}))
            if isinstance(profile.metrics.get("guarded_rollout"), dict)
            else {}
        )
        consecutive_shadow_passes = int(guarded_rollout.get("consecutive_shadow_passes", 0) or 0)
        consecutive_shadow_passes = consecutive_shadow_passes + 1 if promotion_recommended else 0
        guarded_rollout["consecutive_shadow_passes"] = consecutive_shadow_passes
        if promotion_recommended:
            guarded_rollout["last_shadow_pass_at"] = decision_payload["recorded_at"]
        else:
            guarded_rollout["last_shadow_failure_at"] = decision_payload["recorded_at"]

        timeline_kind = "strategy_promotion_shadow"
        if bool(decision_payload.get("applied")) and bool(decision_payload.get("approved")):
            timeline_kind = "strategy_promotion_applied"
        elif bool(decision_payload.get("applied")) and not bool(decision_payload.get("approved")):
            timeline_kind = "strategy_promotion_rollback"
        timeline = [
            {
                "kind": timeline_kind,
                "recorded_at": decision_payload["recorded_at"],
                "strategy_id": strategy_id,
                "baseline_run_id": baseline_summary["run_id"],
                "challenger_run_id": challenger_summary["run_id"],
                "promotion_recommended": promotion_recommended,
                "promotion_decision": decision_payload,
            },
            *[
                item
                for item in profile.metrics.get("decision_timeline", [])
                if isinstance(item, dict)
            ],
        ]
        timeline = sorted(
            timeline,
            key=lambda item: str(item.get("recorded_at") or ""),
            reverse=True,
        )[: self.STRATEGY_DECISION_TIMELINE_LIMIT]

        profile.metrics = {
            **profile.metrics,
            "last_eval_run": {
                "baseline_run_id": baseline_summary["run_id"],
                "challenger_run_id": challenger_summary["run_id"],
                "baseline_success_rate": baseline_summary.get("report", {}).get("success_rate", 0.0),
                "challenger_success_rate": challenger_summary.get("report", {}).get("success_rate", 0.0),
                "baseline_accepted_quality_rate": baseline_summary.get("report", {}).get("quality", {}).get("pass_rate", 0.0),
                "challenger_accepted_quality_rate": challenger_summary.get("report", {}).get("quality", {}).get("pass_rate", 0.0),
                "promotion_mode": str(decision_payload.get("mode") or "shadow"),
                "promotion_recommended": promotion_recommended,
                "promotion_decision": decision_payload,
            },
            "decision_timeline": timeline,
            "guarded_rollout": guarded_rollout,
        }
        return self.create_strategy_profile(profile)
