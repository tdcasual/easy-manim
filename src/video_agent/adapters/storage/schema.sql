CREATE TABLE IF NOT EXISTS video_tasks (
    task_id TEXT PRIMARY KEY,
    root_task_id TEXT NOT NULL,
    parent_task_id TEXT,
    agent_id TEXT,
    session_id TEXT,
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    prompt TEXT NOT NULL,
    feedback TEXT,
    memory_context_summary TEXT,
    memory_context_digest TEXT,
    idempotency_key TEXT UNIQUE,
    current_script_artifact_id TEXT,
    best_result_artifact_id TEXT,
    task_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profiles (
    agent_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    profile_version INTEGER NOT NULL DEFAULT 1,
    profile_json TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_profile_revisions (
    revision_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    patch_json TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_tokens (
    token_hash TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    scopes_json TEXT NOT NULL,
    override_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id TEXT PRIMARY KEY,
    session_hash TEXT NOT NULL UNIQUE,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    source_session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    summary_digest TEXT NOT NULL,
    lineage_refs_json TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    enhancement_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    disabled_at TEXT
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
