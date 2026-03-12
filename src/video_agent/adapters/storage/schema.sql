CREATE TABLE IF NOT EXISTS video_tasks (
    task_id TEXT PRIMARY KEY,
    root_task_id TEXT NOT NULL,
    parent_task_id TEXT,
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    prompt TEXT NOT NULL,
    feedback TEXT,
    idempotency_key TEXT UNIQUE,
    current_script_artifact_id TEXT,
    best_result_artifact_id TEXT,
    task_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_artifacts (
    artifact_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    artifact_kind TEXT NOT NULL,
    path TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_leases (
    task_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    lease_expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    last_seen_at TEXT NOT NULL,
    details_json TEXT NOT NULL
);
