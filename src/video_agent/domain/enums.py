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
    GENERATING_CODE = "generating_code"
    STATIC_CHECK = "static_check"
    RENDERING = "rendering"
    FRAME_EXTRACT = "frame_extract"
    VALIDATION = "validation"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVISION = "needs_revision"
