from __future__ import annotations

from dataclasses import dataclass

from video_agent.adapters.llm.client import LLMClient, StubLLMClient
from video_agent.adapters.llm.openai_compatible_client import OpenAICompatibleLLMClient
from video_agent.adapters.llm.prompt_builder import build_generation_prompt
from video_agent.adapters.rendering.frame_extractor import FrameExtractor
from video_agent.adapters.rendering.manim_runner import ManimRunner
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_learning_service import AgentLearningService
from video_agent.application.agent_identity_service import AgentIdentityService
from video_agent.application.agent_session_service import AgentSessionService
from video_agent.application.auto_repair_service import AutoRepairService
from video_agent.application.persistent_memory_service import PersistentMemoryService, build_persistent_memory_enhancer
from video_agent.application.runtime_service import RuntimeService
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.task_service import TaskService
from video_agent.application.workflow_engine import WorkflowEngine
from video_agent.config import Settings
from video_agent.observability.metrics import MetricsCollector
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
    agent_session_service: AgentSessionService
    session_auth: SessionAuthRegistry
    session_memory_registry: SessionMemoryRegistry
    session_memory_service: SessionMemoryService
    persistent_memory_service: PersistentMemoryService
    agent_learning_service: AgentLearningService
    task_service: TaskService
    workflow_engine: WorkflowEngine
    worker: WorkerLoop
    runtime_service: RuntimeService
    runtime_policy: RuntimePolicy
    metrics: MetricsCollector



def _build_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_provider == "stub":
        return StubLLMClient()
    if settings.llm_provider == "openai_compatible":
        if not settings.llm_base_url:
            raise ValueError("llm_base_url is required for openai_compatible provider")
        if not settings.llm_api_key:
            raise ValueError("llm_api_key is required for openai_compatible provider")
        return OpenAICompatibleLLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")



def create_app_context(settings: Settings) -> AppContext:
    store = SQLiteTaskStore(settings.database_path)
    store.initialize()
    artifact_store = ArtifactStore(settings.artifact_root, eval_root=settings.eval_root)
    agent_identity_service = AgentIdentityService(
        profile_lookup=store.get_agent_profile,
        token_lookup=store.get_agent_token,
    )
    agent_session_service = AgentSessionService(
        authenticate_agent=agent_identity_service.authenticate,
        create_session_record=store.create_agent_session,
        lookup_session_record=store.get_agent_session,
        revoke_session_record=store.revoke_agent_session,
        touch_session_record=store.touch_agent_session,
    )
    session_auth = SessionAuthRegistry()
    session_memory_registry = SessionMemoryRegistry()
    session_memory_service = SessionMemoryService(
        registry=session_memory_registry,
        max_entries=settings.session_memory_max_entries,
        max_attempts_per_entry=settings.session_memory_max_attempts_per_entry,
        summary_char_limit=settings.session_memory_summary_char_limit,
    )
    persistent_memory_service = PersistentMemoryService(
        create_record=store.create_agent_memory,
        get_session_summary=session_memory_service.summarize_session_memory,
        get_record=store.get_agent_memory,
        list_records=store.list_agent_memories,
        disable_record=store.disable_agent_memory,
        enhancer=build_persistent_memory_enhancer(
            backend=settings.persistent_memory_backend,
            enable_embeddings=settings.persistent_memory_enable_embeddings,
            embedding_provider=settings.persistent_memory_embedding_provider,
            embedding_model=settings.persistent_memory_embedding_model,
        ),
    )
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
    )
    runtime_policy = RuntimePolicy(
        work_root=settings.artifact_root,
        render_timeout_seconds=settings.render_timeout_seconds,
        network_disabled=settings.sandbox_network_disabled,
        process_limit=settings.sandbox_process_limit,
        memory_limit_mb=settings.sandbox_memory_limit_mb,
        temp_root=settings.sandbox_temp_root,
    )
    runtime_service = RuntimeService(settings=settings, store=store, runtime_policy=runtime_policy)
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
    )
    workflow_engine.auto_repair_service = AutoRepairService(
        store=store,
        artifact_store=artifact_store,
        settings=settings,
        task_service=task_service,
    )
    worker = WorkerLoop(
        store=store,
        workflow_engine=workflow_engine,
        worker_id=settings.worker_id,
        lease_seconds=settings.worker_lease_seconds,
        recovery_grace_seconds=settings.worker_recovery_grace_seconds,
    )
    return AppContext(
        settings=settings,
        store=store,
        artifact_store=artifact_store,
        agent_identity_service=agent_identity_service,
        agent_session_service=agent_session_service,
        session_auth=session_auth,
        session_memory_registry=session_memory_registry,
        session_memory_service=session_memory_service,
        persistent_memory_service=persistent_memory_service,
        agent_learning_service=agent_learning_service,
        task_service=task_service,
        workflow_engine=workflow_engine,
        worker=worker,
        runtime_service=runtime_service,
        runtime_policy=runtime_policy,
        metrics=metrics,
    )
