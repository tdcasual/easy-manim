from __future__ import annotations

from dataclasses import dataclass

from video_agent.adapters.llm.client import LLMClient, StubLLMClient
from video_agent.adapters.llm.litellm_client import LiteLLMClient
from video_agent.adapters.llm.prompt_builder import build_generation_prompt
from video_agent.adapters.rendering.frame_extractor import FrameExtractor
from video_agent.adapters.rendering.manim_runner import ManimRunner
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_learning_service import AgentLearningService
from video_agent.application.agent_runtime_service import AgentRuntimeDefinitionService
from video_agent.application.agent_runtime_run_service import AgentRuntimeRunService
from video_agent.application.agent_identity_service import AgentIdentityService
from video_agent.application.agent_session_service import AgentSessionService
from video_agent.application.auto_repair_service import AutoRepairService
from video_agent.application.case_reliability_service import CaseReliabilityService
from video_agent.application.case_memory_service import CaseMemoryService
from video_agent.application.capability_gate_service import CapabilityGateService
from video_agent.application.delivery_case_service import DeliveryCaseService
from video_agent.application.multi_agent_workflow_service import MultiAgentWorkflowService
from video_agent.application.persistent_memory_service import (
    PersistentMemoryService,
    build_persistent_memory_backend,
)
from video_agent.application.quality_judge_service import QualityJudgeService
from video_agent.application.recovery_policy_service import RecoveryPolicyService
from video_agent.application.review_bundle_builder import ReviewBundleBuilder
from video_agent.application.runtime_service import RuntimeService
from video_agent.application.scene_spec_service import SceneSpecService
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.task_risk_service import TaskRiskService
from video_agent.application.task_reliability_service import TaskReliabilityService
from video_agent.application.task_service import TaskService
from video_agent.application.video_iteration_service import VideoIterationService
from video_agent.application.video_policy_service import VideoPolicyService
from video_agent.application.video_projection_service import VideoProjectionService
from video_agent.application.video_run_binding_service import VideoRunBindingService
from video_agent.application.video_thread_service import VideoThreadService
from video_agent.application.video_turn_service import VideoTurnService
from video_agent.application.workflow_collaboration_service import WorkflowCollaborationService
from video_agent.application.workflow_loop_policy import WorkflowLoopPolicy
from video_agent.application.workflow_engine import WorkflowEngine
from video_agent.config import DEFAULT_STUB_LLM_MODEL, Settings
from video_agent.observability.metrics import MetricsCollector
from video_agent.openclaw.gateway_sessions import GatewaySessionPolicy, GatewaySessionService
from video_agent.safety.runtime_policy import RuntimePolicy
from video_agent.server.session_auth import SessionAuthRegistry
from video_agent.server.session_memory import SessionMemoryRegistry
from video_agent.validation.hard_validation import HardValidator
from video_agent.validation.rule_validation import RuleValidator
from video_agent.validation.static_check import StaticCheckValidator
from video_agent.worker.worker_loop import WorkerLoop


@dataclass
class AppContext:
    settings: Settings
    store: SQLiteTaskStore
    artifact_store: ArtifactStore
    agent_identity_service: AgentIdentityService
    agent_runtime_definition_service: AgentRuntimeDefinitionService
    agent_runtime_run_service: AgentRuntimeRunService
    agent_session_service: AgentSessionService
    session_auth: SessionAuthRegistry
    gateway_session_service: GatewaySessionService
    session_memory_registry: SessionMemoryRegistry
    session_memory_service: SessionMemoryService
    persistent_memory_service: PersistentMemoryService
    agent_learning_service: AgentLearningService
    delivery_case_service: DeliveryCaseService
    case_memory_service: CaseMemoryService
    task_service: TaskService
    task_risk_service: TaskRiskService
    case_reliability_service: CaseReliabilityService
    task_reliability_service: TaskReliabilityService
    video_thread_service: VideoThreadService
    video_iteration_service: VideoIterationService
    video_turn_service: VideoTurnService
    video_run_binding_service: VideoRunBindingService
    video_policy_service: VideoPolicyService
    video_projection_service: VideoProjectionService
    scene_spec_service: SceneSpecService
    capability_gate_service: CapabilityGateService
    recovery_policy_service: RecoveryPolicyService
    quality_judge_service: QualityJudgeService
    workflow_collaboration_service: WorkflowCollaborationService
    review_bundle_builder: ReviewBundleBuilder
    multi_agent_workflow_service: MultiAgentWorkflowService
    workflow_engine: WorkflowEngine
    worker: WorkerLoop
    runtime_service: RuntimeService
    runtime_policy: RuntimePolicy
    metrics: MetricsCollector



def _build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "stub":
        return StubLLMClient()
    if settings.llm_provider == "litellm":
        if not settings.llm_model or settings.llm_model == DEFAULT_STUB_LLM_MODEL:
            raise ValueError("llm_model must be set to a real model when llm_provider=litellm")
        return LiteLLMClient(
            model=settings.llm_model,
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")


def _build_store(settings: Settings) -> SQLiteTaskStore:
    SQLiteBootstrapper(settings.database_path).require_bootstrapped(data_dir=settings.data_dir)
    return SQLiteTaskStore(
        settings.database_path,
        agent_runtime_root=settings.agent_runtime_root,
    )



def create_app_context(settings: Settings) -> AppContext:
    store = _build_store(settings)
    artifact_store = ArtifactStore(settings.artifact_root, eval_root=settings.eval_root)
    agent_runtime_definition_service = AgentRuntimeDefinitionService(
        definition_lookup=store.get_agent_runtime_definition,
        definition_upsert=store.upsert_agent_runtime_definition,
        default_workspace_root=settings.agent_runtime_root,
    )
    agent_identity_service = AgentIdentityService(
        profile_lookup=store.get_agent_profile,
        token_lookup=store.get_agent_token,
        runtime_definition_resolver=lambda agent_id, profile: agent_runtime_definition_service.require_persisted(agent_id),
    )
    agent_runtime_run_service = AgentRuntimeRunService(
        create_run=store.create_agent_runtime_run,
        list_runs=store.list_agent_runtime_runs,
    )
    agent_session_service = AgentSessionService(
        authenticate_agent=agent_identity_service.authenticate,
        create_session_record=store.create_agent_session,
        lookup_session_record=store.get_agent_session,
        revoke_session_record=store.revoke_agent_session,
        touch_session_record=store.touch_agent_session,
    )
    session_auth = SessionAuthRegistry()
    gateway_session_service = GatewaySessionService(
        policy=GatewaySessionPolicy(
            dm_scope=settings.gateway_session_dm_scope,
            daily_reset_hour_local=settings.gateway_session_daily_reset_hour_local,
            idle_reset_minutes=settings.gateway_session_idle_reset_minutes,
        )
    )
    session_memory_registry = SessionMemoryRegistry(
        load_snapshot=store.get_session_memory_snapshot,
        persist_snapshot=store.upsert_session_memory_snapshot,
        list_persisted_snapshots=store.list_session_memory_snapshots,
    )
    session_memory_service = SessionMemoryService(
        registry=session_memory_registry,
        max_entries=settings.session_memory_max_entries,
        max_attempts_per_entry=settings.session_memory_max_attempts_per_entry,
        summary_char_limit=settings.session_memory_summary_char_limit,
    )
    persistent_memory_backend = build_persistent_memory_backend(
        backend=settings.persistent_memory_backend,
        enable_embeddings=settings.persistent_memory_enable_embeddings,
        embedding_provider=settings.persistent_memory_embedding_provider,
        embedding_model=settings.persistent_memory_embedding_model,
        memo0_api_key=settings.persistent_memory_memo0_api_key,
        memo0_org_id=settings.persistent_memory_memo0_org_id,
        memo0_project_id=settings.persistent_memory_memo0_project_id,
    )
    persistent_memory_service = PersistentMemoryService(
        create_record=store.create_agent_memory,
        get_session_summary=session_memory_service.summarize_session_memory,
        get_record=store.get_agent_memory,
        list_records=store.list_agent_memories,
        disable_record=store.disable_agent_memory,
        enhancer=persistent_memory_backend,
        memory_backend=persistent_memory_backend,
    )
    video_iteration_service = VideoIterationService(store=store)
    video_turn_service = VideoTurnService(store=store)
    video_run_binding_service = VideoRunBindingService(store=store)
    delivery_case_service = DeliveryCaseService(
        store=store,
        artifact_store=artifact_store,
        video_run_binding_service=video_run_binding_service,
    )
    case_memory_service = CaseMemoryService(artifact_store=artifact_store)
    agent_learning_service = AgentLearningService(
        write_event=store.create_agent_learning_event,
        list_events=store.list_agent_learning_events,
    )
    task_service = TaskService(
        store=store,
        artifact_store=artifact_store,
        settings=settings,
        session_memory_service=session_memory_service,
        persistent_memory_service=persistent_memory_service,
        delivery_case_service=delivery_case_service,
        case_memory_service=case_memory_service,
    )
    task_risk_service = TaskRiskService()
    video_policy_service = VideoPolicyService()
    video_projection_service = VideoProjectionService(store=store)
    video_thread_service = VideoThreadService(
        store=store,
        iteration_service=video_iteration_service,
        turn_service=video_turn_service,
        task_service=task_service,
    )
    scene_spec_service = SceneSpecService()
    capability_gate_service = CapabilityGateService()
    recovery_policy_service = RecoveryPolicyService()
    quality_judge_service = QualityJudgeService(min_score=settings.quality_gate_min_score)
    workflow_collaboration_service = WorkflowCollaborationService(
        store=store,
        task_service=task_service,
        persistent_memory_service=persistent_memory_service,
        case_memory_service=case_memory_service,
    )
    review_bundle_builder = ReviewBundleBuilder(
        task_service=task_service,
        collaboration_service=workflow_collaboration_service,
        store=store,
        session_memory_service=session_memory_service,
        case_memory_service=case_memory_service,
    )
    multi_agent_workflow_service = MultiAgentWorkflowService(
        enabled=settings.multi_agent_workflow_enabled,
        bundle_builder=review_bundle_builder,
        collaboration_service=workflow_collaboration_service,
        task_service=task_service,
        policy=WorkflowLoopPolicy(settings),
    )
    runtime_policy = RuntimePolicy(
        work_root=settings.artifact_root,
        render_timeout_seconds=settings.render_timeout_seconds,
        network_disabled=settings.sandbox_network_disabled,
        process_limit=settings.sandbox_process_limit,
        memory_limit_mb=settings.sandbox_memory_limit_mb,
        temp_root=settings.sandbox_temp_root,
    )
    runtime_service = RuntimeService(
        settings=settings,
        store=store,
        runtime_policy=runtime_policy,
        collaboration_service=workflow_collaboration_service,
    )
    metrics = MetricsCollector()
    workflow_engine = WorkflowEngine(
        store=store,
        artifact_store=artifact_store,
        llm_client=_build_llm_client(settings),
        prompt_builder=build_generation_prompt,
        static_validator=StaticCheckValidator(),
        manim_runner=ManimRunner(command=settings.manim_command, base_env=settings.render_environment),
        frame_extractor=FrameExtractor(command=settings.ffmpeg_command),
        hard_validator=HardValidator(command=settings.ffprobe_command),
        rule_validator=RuleValidator(),
        runtime_service=runtime_service,
        agent_learning_service=agent_learning_service,
        session_memory_service=session_memory_service,
        runtime_policy=runtime_policy,
        metrics=metrics,
        task_risk_service=task_risk_service,
        scene_spec_service=scene_spec_service,
        capability_gate_service=capability_gate_service,
        recovery_policy_service=recovery_policy_service,
        quality_judge_service=quality_judge_service,
        delivery_case_service=delivery_case_service,
        case_memory_service=case_memory_service,
    )
    workflow_engine.auto_repair_service = AutoRepairService(
        store=store,
        artifact_store=artifact_store,
        settings=settings,
        task_service=task_service,
        recovery_policy_service=recovery_policy_service,
    )
    case_reliability_service = CaseReliabilityService(
        settings=settings,
        store=store,
        artifact_store=artifact_store,
        runtime_service=runtime_service,
        workflow_engine=workflow_engine,
        metrics=metrics,
    )
    task_reliability_service = TaskReliabilityService(
        case_reliability_service=case_reliability_service,
    )
    worker = WorkerLoop(
        store=store,
        workflow_engine=workflow_engine,
        task_reliability_service=case_reliability_service,
        worker_id=settings.worker_id,
        lease_seconds=settings.worker_lease_seconds,
        recovery_grace_seconds=settings.worker_recovery_grace_seconds,
    )
    case_reliability_service.reconcile_startup()
    return AppContext(
        settings=settings,
        store=store,
        artifact_store=artifact_store,
        agent_identity_service=agent_identity_service,
        agent_runtime_definition_service=agent_runtime_definition_service,
        agent_runtime_run_service=agent_runtime_run_service,
        agent_session_service=agent_session_service,
        session_auth=session_auth,
        gateway_session_service=gateway_session_service,
        session_memory_registry=session_memory_registry,
        session_memory_service=session_memory_service,
        persistent_memory_service=persistent_memory_service,
        agent_learning_service=agent_learning_service,
        delivery_case_service=delivery_case_service,
        case_memory_service=case_memory_service,
        task_service=task_service,
        task_risk_service=task_risk_service,
        case_reliability_service=case_reliability_service,
        task_reliability_service=task_reliability_service,
        video_thread_service=video_thread_service,
        video_iteration_service=video_iteration_service,
        video_turn_service=video_turn_service,
        video_run_binding_service=video_run_binding_service,
        video_policy_service=video_policy_service,
        video_projection_service=video_projection_service,
        scene_spec_service=scene_spec_service,
        capability_gate_service=capability_gate_service,
        recovery_policy_service=recovery_policy_service,
        quality_judge_service=quality_judge_service,
        workflow_collaboration_service=workflow_collaboration_service,
        review_bundle_builder=review_bundle_builder,
        multi_agent_workflow_service=multi_agent_workflow_service,
        workflow_engine=workflow_engine,
        worker=worker,
        runtime_service=runtime_service,
        runtime_policy=runtime_policy,
        metrics=metrics,
    )
