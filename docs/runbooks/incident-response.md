# Incident Response

## Server starts but tasks never progress
- Symptom: tasks remain `queued` and `get_runtime_status` shows no healthy worker heartbeat
- Likely cause: standalone worker is not running, or its heartbeat has gone stale
- First checks:
  - `easy-manim-doctor --json`
  - inspect MCP tool `get_runtime_status`
  - confirm `easy-manim-worker --data-dir data` is running
- Exact commands:
```bash
source .venv/bin/activate
easy-manim-doctor --json
easy-manim-worker --data-dir data
```
- Escalation boundary: if heartbeats remain stale while the process is up, inspect SQLite permissions and task lease rows

## New tasks are rejected immediately
- Symptom: `create_video_task` returns `queue_full`
- Likely cause: active queue reached `EASY_MANIM_MAX_QUEUED_TASKS`
- First checks:
  - inspect `list_video_tasks`
  - inspect `get_runtime_status` worker freshness
  - verify tasks are draining
- Exact commands:
```bash
source .venv/bin/activate
easy-manim-doctor --json
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --dry-run
```
- Escalation boundary: only raise queue limits after verifying the worker throughput bottleneck is understood

## Retry path is blocked
- Symptom: `retry_video_task` returns `attempt_limit_reached`
- Likely cause: the task lineage already hit `EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK`
- First checks:
  - inspect the parent task history with `get_task_events`
  - export the task bundle before changing limits
- Exact commands:
```bash
source .venv/bin/activate
easy-manim-export-task --data-dir data --task-id <task_id> --output /tmp/<task_id>.zip
```
- Escalation boundary: raise the retry cap only after capturing a support bundle and deciding why retries are repeating

## Rendering or validation suddenly fails
- Symptom: task reaches `failed` with `render_failed`, `runtime_policy_violation`, or `infra_error`
- Likely cause: local binaries changed, output paths are invalid, or a local exception escaped normalization
- First checks:
  - `easy-manim-doctor --json`
  - inspect `data/tasks/<task_id>/artifacts/failure_context.json`
  - inspect `data/tasks/<task_id>/logs/events.jsonl`
  - inspect `data/tasks/<task_id>/validations/validation_report_v1.json`
- Exact commands:
```bash
source .venv/bin/activate
easy-manim-doctor --json
cat data/tasks/<task_id>/artifacts/failure_context.json
cat data/tasks/<task_id>/logs/events.jsonl
cat data/tasks/<task_id>/validations/validation_report_v1.json
```
- Escalation boundary: if diagnostics show correct binaries and reproducible failures, capture the exported task bundle and escalate with logs
