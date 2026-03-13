# Beta Operations Runbook

## Required environment
- Python virtualenv with `easy-manim` installed in editable mode
- `ffmpeg`, `ffprobe`, and `manim` available, or explicit overrides via:
  - `EASY_MANIM_MANIM_COMMAND`
  - `EASY_MANIM_FFMPEG_COMMAND`
  - `EASY_MANIM_FFPROBE_COMMAND`
- optional real provider config:
  - `EASY_MANIM_LLM_PROVIDER=openai_compatible`
  - `EASY_MANIM_LLM_MODEL=<model>`
  - `EASY_MANIM_LLM_BASE_URL=<base_url>`
  - `EASY_MANIM_LLM_API_KEY=<api_key>`
- beta / RC guardrails:
  - `EASY_MANIM_RELEASE_CHANNEL`
  - `EASY_MANIM_WORKER_STALE_AFTER_SECONDS`
  - `EASY_MANIM_MAX_QUEUED_TASKS`
  - `EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK`

## Preflight
```bash
source .venv/bin/activate
easy-manim-doctor --json
python scripts/release_candidate_gate.py --mode ci
```

## Start the beta stack
```bash
source .venv/bin/activate
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

## Runtime inspection
- Call MCP tool `get_runtime_status` to inspect:
  - resolved binary paths
  - provider configuration mode
  - embedded-vs-standalone worker mode
  - worker heartbeat freshness
  - release metadata (`version` and `channel`)
- Call `get_metrics_snapshot` to inspect counters and timings
- Call `list_video_tasks` and `get_task_events` to inspect queue state and per-task history

## Create and inspect a task
1. Connect an MCP client to `http://127.0.0.1:8000/mcp`
2. Call `create_video_task` with a prompt
3. Poll `get_video_task` until terminal status
4. Call `get_video_result`
5. If needed, inspect:
   - `data/tasks/<task_id>/task.json`
   - `data/tasks/<task_id>/logs/events.jsonl`
   - `data/tasks/<task_id>/validations/validation_report_v1.json`

You can tighten validation per task with `validation_profile`, for example:

```json
{
  "min_duration_seconds": 5.0,
  "min_width": 1280,
  "min_height": 720,
  "check_black_frames": true
}
```

- use higher thresholds for release-candidate prompts
- disable a heuristic only when the operator understands the tradeoff and the task bundle will still be reviewed manually

## Deterministic evaluation runs
Use the smoke subset for deterministic checks:

```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag smoke --json
```

Artifacts are written under `data/evals/<run_id>/`:
- `summary.json`
- `summary.md`

Export a reviewer bundle with:

```bash
source .venv/bin/activate
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

## Release-candidate trial flow
- copy `.env.beta.example` to `.env.beta`
- load the real-provider credentials into the shell
- run `easy-manim-eval-run --include-tag real-provider --json`
- export a qa bundle for the resulting `run_id`
- record the decision using `docs/templates/release-candidate-decision.md`
- follow the detailed procedure in `docs/runbooks/real-provider-trial.md`

## Queue and retry guardrails
- `queue_full`: too many active queued/running/revising tasks; wait for drain or raise `EASY_MANIM_MAX_QUEUED_TASKS`
- `attempt_limit_reached`: a retry lineage exceeded `EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK`; export the task bundle before raising the cap
- auto-repair is opt-in via `EASY_MANIM_AUTO_REPAIR_ENABLED`; keep `EASY_MANIM_AUTO_REPAIR_MAX_CHILDREN_PER_ROOT` small because it is a bounded assist, not a substitute for operator review
- limit auto-repair to explicitly retryable issue codes with `EASY_MANIM_AUTO_REPAIR_RETRYABLE_ISSUE_CODES`

## Worker heartbeat interpretation
- a recent worker heartbeat with `stale=false` means the worker loop is alive
- `stale=true` means the worker has not updated within `EASY_MANIM_WORKER_STALE_AFTER_SECONDS`
- if the server uses `--no-embedded-worker`, stale or missing heartbeats usually mean the standalone worker is down

## Common failure signatures
- `provider_auth_error`: provider credentials are missing or invalid
- `provider_rate_limited`: upstream model quota or rate limit hit
- `provider_timeout`: upstream model request exceeded timeout
- `generation_failed`: provider returned malformed or unusable content
- `render_failed`: Manim process failed or output file missing
- `runtime_policy_violation`: artifact write target escaped the allowed work root
- `infra_error`: unexpected local exception outside normalized failure mapping
- `queue_full`: admission control rejected a new task
- `attempt_limit_reached`: admission control rejected a retry

## Semantic repair inspection
- inspect `data/tasks/<task_id>/artifacts/failure_context.json` for `semantic_diagnostics`
- expect structured entries such as:
  - `unsupported_helper_kwargs`
  - `coordinate_object_method_call`
  - `missing_scene_subclass`
- if auto-repair is enabled, confirm `get_video_task` and `get_task_events` show an `auto_repair_decision`, then inspect the child task feedback for the targeted-repair instructions and source script resource
- `auto_repair_created` events should now surface revision metadata such as `revision_mode=targeted_repair` and `preserve_working_parts=true`

## Cleanup old beta data
```bash
source .venv/bin/activate
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --dry-run
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --confirm
```

## Export a task bundle for support
```bash
source .venv/bin/activate
easy-manim-export-task --data-dir data --task-id <task_id> --output /tmp/<task_id>.zip
```

## First checks when something breaks
- run `easy-manim-doctor --json`
- run `python scripts/release_candidate_gate.py --mode ci` for a deterministic local gate
- inspect `get_runtime_status` for missing binaries, provider config, stale workers, and release metadata
- verify `easy-manim-worker` is running if the server started with `--no-embedded-worker`
- inspect `logs/events.jsonl` for the latest task phase and error message
- inspect `get_task_events` for the failing task
- check `validation_report_v1.json` for normalized issue codes
- confirm the configured `manim`, `ffmpeg`, and `ffprobe` binaries are reachable
