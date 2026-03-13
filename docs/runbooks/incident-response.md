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

## Auto-repair stops creating children
- Symptom: task snapshots show `auto_repair_summary.stopped_reason`
- Likely cause: auto-repair is disabled, the issue code is not retryable, or the lineage already exhausted `EASY_MANIM_AUTO_REPAIR_MAX_CHILDREN_PER_ROOT`
- First checks:
  - inspect MCP tool `get_video_task`
  - inspect `repair_state` on the root task snapshot for the latest issue code and whether repair was attempted
  - inspect `data/tasks/<root_task_id>/logs/events.jsonl`
  - verify the configured retryable issue codes and child budget
- Exact commands:
```bash
source .venv/bin/activate
cat data/tasks/<root_task_id>/logs/events.jsonl
```
- Escalation boundary: raise the budget only after confirming the last child failed for a genuinely fixable issue rather than repeating the same root cause

## Rendering or validation suddenly fails
- Symptom: task reaches `failed` with `render_failed`, `runtime_policy_violation`, or `infra_error`
- Likely cause: local binaries changed, output paths are invalid, or a local exception escaped normalization
- First checks:
  - `easy-manim-doctor --json`
  - inspect `get_video_task` for `auto_repair_summary`
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

## Sandbox policy blocks render launch
- Symptom: task reaches `failed` with `sandbox_policy_violation`
- Likely cause: configured sandbox temp root escaped the artifact work root, or the local sandbox profile no longer matches the current data directory
- First checks:
  - inspect `get_runtime_status` for the `sandbox` section
  - inspect `data/tasks/<task_id>/artifacts/failure_context.json` for `sandbox_policy`
  - confirm `EASY_MANIM_SANDBOX_TEMP_ROOT` remains under `data/tasks/`
- Exact commands:
```bash
source .venv/bin/activate
cat data/tasks/<task_id>/artifacts/failure_context.json
```
- Escalation boundary: only relax sandbox settings after confirming the temp root is intentionally outside the artifact root
