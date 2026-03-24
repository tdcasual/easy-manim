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
- auth controls:
  - `EASY_MANIM_AUTH_MODE` with `disabled` or `required`
  - `EASY_MANIM_ANONYMOUS_AGENT_ID` for the fallback local identity in disabled mode

## Preflight
```bash
source .venv/bin/activate
easy-manim-doctor --json
python scripts/release_candidate_gate.py --mode ci
```

Bootstrap the local SQLite database once before the standalone server, worker, admin, eval, or cleanup commands below:

```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
```

## Start the beta stack
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

To require named-agent authentication:

```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

To expose the plain HTTP JSON API instead of MCP:

```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-db-bootstrap --data-dir data
easy-manim-api --host 127.0.0.1 --port 8001 --data-dir data --no-embedded-worker
easy-manim-worker --data-dir data
```

## Provision agent identities
Create a profile and issue a token before handing access to an external agent:

```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-agent-admin --data-dir data create-profile --agent-id agent-a --name "Agent A"
easy-manim-agent-admin --data-dir data issue-token --agent-id agent-a
```

Notes:
- `create-profile` accepts `--profile-json` for per-agent defaults such as `style_hints`, `output_profile`, or `validation_profile`
- `issue-token` accepts `--override-json` when a specific token should override part of the profile defaults
- the plaintext token is shown exactly once; only `token_hash` is stored, so lost plaintext tokens must be rotated, not recovered
- use `easy-manim-agent-admin --data-dir data inspect-profile --agent-id agent-a` to list issued token hashes
- use `easy-manim-agent-admin --data-dir data disable-token --token-hash <token_hash>` to revoke one token without deleting the profile

For HTTP clients, exchange the plaintext token once:

```bash
SESSION_TOKEN=$(
  curl -s http://127.0.0.1:8001/api/sessions \
    -H 'content-type: application/json' \
    -d '{"agent_token":"<plaintext-agent-token>"}' | jq -r '.session_token'
)
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
- For failed tasks, call `get_video_task` or `get_failure_contract` to inspect the machine-decidable `failure_contract`

## Create and inspect a task
1. Connect an MCP client to `http://127.0.0.1:8000/mcp`
2. If `EASY_MANIM_AUTH_MODE=required`, call `authenticate_agent` with the issued plaintext token
3. Call `create_video_task` with a prompt
4. Poll `get_video_task` until terminal status
5. Call `get_video_result`
6. If needed, inspect:
   - `data/tasks/<task_id>/task.json`
   - `data/tasks/<task_id>/logs/events.jsonl`
   - `data/tasks/<task_id>/artifacts/scene_plan.json`
   - `data/tasks/<task_id>/validations/validation_report_v1.json`

You can pass `style_hints` alongside `prompt`, `output_profile`, and `validation_profile` when creating a task. Use it for operator-controlled guidance such as tone, pacing, or layout intent; the workflow will persist a deterministic scene plan before generation.

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
- preview quality checks may add issue codes such as `near_blank_preview` and `static_previews`; treat them as visual quality failures even when the render technically succeeded

## Deterministic evaluation runs
Use the smoke subset for deterministic checks:

```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag smoke --json
```

Use the quality slice when you want a narrow read on visual quality regressions:

```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag quality --json
```

Use the real-provider quality intersection when you want only prompts that are both manually supervised and quality-sensitive:

```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag real-provider --include-tag quality --match-all-tags --json
```

Artifacts are written under `data/evals/<run_id>/`:
- `summary.json`
- `summary.md`
- `review_digest.md`

Quality-enabled eval summaries now include `report.quality`, with pass-rate, median quality score, and aggregated quality issue counts. The CLI text output also prints `quality_pass_rate=...` for quick inspection.
Agent-targeted evals can also include:

```bash
source .venv/bin/activate
easy-manim-eval-run \
  --data-dir data \
  --suite evals/beta_prompt_suite.json \
  --include-tag smoke \
  --agent-id agent-a \
  --memory-id mem-1 \
  --profile-patch-json '{"style_hints":{"tone":"teaching"}}' \
  --json
```

These runs emit `report.agent` in `summary.json`, plus an `Agent Slice` section in `summary.md` and `review_digest.md`.

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
- `near_blank_preview`: preview frames start effectively blank
- `static_previews`: preview frames show too little motion across the sampled sequence

## Failure contract interpretation
- `failure_contract.retryable=true` means an upstream agent may safely attempt another automated step without first asking a human
- `recommended_action=auto_repair` is trustworthy for normalized render, validation, and preview failures that map to the configured retryable issue-code set
- `recommended_action=fix_credentials` means stop autonomous retries and repair the provider configuration before running again
- `recommended_action=retry_later` usually indicates transient provider pressure such as timeout or rate limiting
- `human_review_required=true` means the local system does not have enough confidence for unattended retries; export the task bundle and inspect the failure context before continuing
- inspect `data/tasks/<task_id>/artifacts/failure_contract.json` when you need the contract outside MCP

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
- inspect `artifacts/scene_plan.json` to confirm the planner chose the expected scene class, transition style, and animation recipes
- check `validation_report_v1.json` for normalized issue codes
- confirm the configured `manim`, `ffmpeg`, and `ffprobe` binaries are reachable
