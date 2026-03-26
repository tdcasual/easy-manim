# easy-manim

A local-first validated video agent for Manim generation.

## What exists today
- Async-style task creation with `task_id`
- SQLite-backed task store and local artifact directories
- Worker pipeline for prompt -> script -> static check -> render -> frame extraction -> validation
- Revision lineage, retry flow, and task cancellation
- Task list, event history, metrics snapshot, runtime status, and structured task logs
- Optional embedded worker or separate worker process with persisted heartbeats
- Operator CLIs for doctor, cleanup, task export, evaluation runs, and qa bundles
- A reusable beta smoke harness and release-candidate-gate for local and CI verification

## Quick start
```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/beta_smoke.py --mode ci
python scripts/release_candidate_gate.py --mode ci
```

## Check runtime prerequisites
```bash
source .venv/bin/activate
easy-manim-doctor --json
```

For formula-heavy scenes that may use `MathTex` or `Tex`, also run:

```bash
source .venv/bin/activate
easy-manim-doctor --json --require-latex
```

## Run the MCP server
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport stdio
```

## Run the HTTP API
```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-db-bootstrap --data-dir data
easy-manim-api --host 127.0.0.1 --port 8001 --data-dir data --no-embedded-worker
easy-manim-worker --data-dir data
```

Log in once, then reuse the returned session token:

```bash
SESSION_TOKEN=$(
  curl -s http://127.0.0.1:8001/api/sessions \
    -H 'content-type: application/json' \
    -d '{"agent_token":"<plaintext-agent-token>"}' | jq -r '.session_token'
)

curl -s http://127.0.0.1:8001/api/whoami \
  -H "Authorization: Bearer ${SESSION_TOKEN}"

TASK_ID=$(
  curl -s http://127.0.0.1:8001/api/tasks \
    -H 'content-type: application/json' \
    -H "Authorization: Bearer ${SESSION_TOKEN}" \
    -d '{"prompt":"draw a blue circle"}' | jq -r '.task_id'
)

curl -s -X DELETE http://127.0.0.1:8001/api/sessions/current \
  -H "Authorization: Bearer ${SESSION_TOKEN}"
```

### Browse the operator console

With the API running, the React console now exposes two primary browser surfaces:

- `/tasks` for Chinese-first task creation, queue review, and title-first task cards
- `/videos` for recent playable outputs aggregated from `GET /api/videos/recent`

Task and video cards now prefer the backend `display_title` while still keeping `task_id` visible as secondary metadata in list/detail views.

### Download artifacts over HTTP

Once a task completes, clients can stay fully on the HTTP API and download task artifacts directly.

`GET /api/tasks/{task_id}/result` now includes convenience URLs when artifacts exist:

- `video_download_url`
- `preview_download_urls`
- `script_download_url`
- `validation_report_download_url`

Example:

```bash
curl -s http://127.0.0.1:8001/api/tasks/${TASK_ID}/result \
  -H "Authorization: Bearer ${SESSION_TOKEN}"

curl -L http://127.0.0.1:8001/api/tasks/${TASK_ID}/artifacts/final_video.mp4 \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -o final_video.mp4

curl -L http://127.0.0.1:8001/api/tasks/${TASK_ID}/artifacts/current_script.py \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -o current_script.py
```

Supported HTTP artifact paths include files under:

- `artifacts/` via `/api/tasks/{task_id}/artifacts/...`
- `validations/` via `/api/tasks/{task_id}/artifacts/validations/...`
- `logs/` via `/api/tasks/{task_id}/artifacts/logs/...`

This enables pure API clients to fetch `final_video.mp4` without SSH, Docker volume access, or Coolify-specific paths.

### Agent Auth Modes
- `EASY_MANIM_AUTH_MODE=disabled` keeps the local developer flow: task tools work without session authentication and tasks are attributed to `local-anonymous` by default.
- `EASY_MANIM_AUTH_MODE=required` makes mutating task tools and task resources require an authenticated agent session.
- `EASY_MANIM_ANONYMOUS_AGENT_ID` lets you rename the local fallback identity used only in `disabled` mode.

Example:

```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

## Provision named agents
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-agent-admin --data-dir data create-profile --agent-id agent-a --name "Agent A"
easy-manim-agent-admin --data-dir data issue-token --agent-id agent-a
```

`issue-token` prints the plaintext token once as JSON. The database stores only `token_hash`, so a lost plaintext token cannot be recovered and must be re-issued.

You can preconfigure per-agent defaults with JSON payloads:

```bash
easy-manim-db-bootstrap --data-dir data
easy-manim-agent-admin --data-dir data create-profile \
  --agent-id agent-a \
  --name "Agent A" \
  --profile-json '{"style_hints":{"tone":"teaching","pace":"steady"}}'
```

After the client receives a plaintext token, it should call the MCP tool `authenticate_agent(agent_token)` once per session before creating or revising tasks in `required` mode.

## Run server and worker separately
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

## Run deterministic evaluations
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag smoke --json
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag smoke --agent-id agent-a --memory-id mem-1 --profile-patch-json '{"style_hints":{"tone":"teaching"}}' --json
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

Evaluation artifacts are written under `data/evals/<run_id>/` and include `summary.json`, `summary.md`, and `review_digest.md`. Agent-targeted evals also emit `report.agent` plus an `Agent Slice` in the markdown summaries.

## Release-candidate flow
```bash
source .venv/bin/activate
cp .env.beta.example .env.beta
python scripts/release_candidate_gate.py --mode ci
easy-manim-db-bootstrap --data-dir data
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag real-provider --json
python scripts/live_provider_gate.py --summary data/evals/<run_id>/summary.json
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

Use `docs/runbooks/real-provider-trial.md` for the trial procedure and `docs/templates/release-candidate-decision.md` to record the go / no-go decision.
If the real-provider prompts may render formulas, make sure `latex` and `dvisvgm` are available first.

## Inspect and maintain beta data
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --dry-run
easy-manim-export-task --data-dir data --task-id <task_id> --output /tmp/<task_id>.zip
```

## Container workflow
```bash
cp .env.example .env
docker login ghcr.io -u <github-user>
docker compose pull
docker compose up -d
```

For a real provider deployment, merge the LiteLLM-oriented `EASY_MANIM_LLM_*` values from `.env.beta.example` into `.env` before starting the stack.

The repository now ships two GitHub Actions-built images:

- `ghcr.io/<owner>/easy-manim` for `easy-manim-api`, `easy-manim-worker`, `easy-manim-mcp`, and admin/eval CLIs
- `ghcr.io/<owner>/easy-manim-ui` for the operator console served by Nginx

The default [docker-compose.yml](/Users/lvxiaoer/Documents/codeWork/easy-manim/docker-compose.yml) is deployment-first and starts:

- `bootstrap` once to apply SQLite migrations on `/app/data/video_agent.db`
- `api` on port `8001`
- `worker` sharing the same `/app/data` volume
- `ui` on port `8080`
- optional `mcp` on port `8000` behind the `mcp` profile

`api`, `worker`, and `mcp` now wait for the bootstrap job to complete successfully before they start.

Enable the MCP endpoint only when needed:

```bash
docker compose --profile mcp up -d mcp
```

For local source builds instead of pulling GHCR images:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

For an image-only, agent-focused deployment and usage walkthrough that does not assume a source checkout on the target host, use `docs/runbooks/agent-self-serve.md`.

To issue or rotate an agent token inside the Compose stack:

```bash
docker compose run --rm api \
  easy-manim-agent-admin --data-dir /app/data issue-token --agent-id agent-a
```

## Important paths
- Phase 2 plan: `docs/plans/2026-03-12-phase-2-beta-readiness-implementation-plan.md`
- Phase 3 plan: `docs/plans/2026-03-12-phase-3-beta-trial-hardening-implementation-plan.md`
- Phase 4 plan: `docs/plans/2026-03-12-phase-4-real-beta-validation-and-release-candidate-implementation-plan.md`
- Local dev guide: `docs/runbooks/local-dev.md`
- Agent self-serve guide: `docs/runbooks/agent-self-serve.md`
- Beta ops guide: `docs/runbooks/beta-ops.md`
- HTTP API deploy guide: `docs/runbooks/http-api-deploy.md`
- Real-provider trial guide: `docs/runbooks/real-provider-trial.md`
- Release checklist: `docs/runbooks/release-checklist.md`
- RC decision template: `docs/templates/release-candidate-decision.md`
- Incident response: `docs/runbooks/incident-response.md`
