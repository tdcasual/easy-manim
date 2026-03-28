from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPhase(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RISK_ROUTING = "risk_routing"
    SCENE_PLANNING = "scene_planning"
    GENERATING_CODE = "generating_code"
    STATIC_CHECK = "static_check"
    PREFLIGHT_CHECK = "preflight_check"
    PREVIEW_RENDER = "preview_render"
    PREVIEW_VALIDATION = "preview_validation"
    RENDERING = "rendering"
    FRAME_EXTRACT = "frame_extract"
    VALIDATION = "validation"
    QUALITY_JUDGING = "quality_judging"
    ESCALATED = "escalated"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVISION = "needs_revision"
