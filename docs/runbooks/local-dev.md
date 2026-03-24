# Local Development

## Prerequisites
- Python 3.10+ available on PATH in this workspace
- `ffmpeg` and `ffprobe` installed and available on PATH
- Manim Community installed and available as `manim`
- For `MathTex` / `Tex` scenes, a TeX toolchain that exposes `latex` and `dvisvgm`

## Environment setup
```bash
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Configuration
- copy `.env.example` to `.env` or export matching `EASY_MANIM_*` variables in your shell
- `stub` mode is the default local mode and keeps tests deterministic
- set `EASY_MANIM_LLM_PROVIDER=openai_compatible` plus provider credentials when using a real upstream model
- override `EASY_MANIM_MANIM_COMMAND`, `EASY_MANIM_FFMPEG_COMMAND`, and `EASY_MANIM_FFPROBE_COMMAND` when testing with custom binaries
- override `EASY_MANIM_LATEX_COMMAND` and `EASY_MANIM_DVISVGM_COMMAND` when TeX tools are not discoverable on PATH
- use `EASY_MANIM_MAX_QUEUED_TASKS` and `EASY_MANIM_MAX_ATTEMPTS_PER_ROOT_TASK` to tune beta safety rails
- production render defaults:
  - `EASY_MANIM_DEFAULT_QUALITY_PRESET=development|preview|production`
  - `EASY_MANIM_DEFAULT_FRAME_RATE=<positive integer>`
  - `EASY_MANIM_DEFAULT_PIXEL_WIDTH=<positive integer>`
  - `EASY_MANIM_DEFAULT_PIXEL_HEIGHT=<positive integer>`
  - per-task `output_profile` values still override these defaults
- sandbox controls:
  - `EASY_MANIM_RENDER_TIMEOUT_SECONDS`
  - `EASY_MANIM_SANDBOX_NETWORK_DISABLED`
  - `EASY_MANIM_SANDBOX_PROCESS_LIMIT`
  - `EASY_MANIM_SANDBOX_MEMORY_LIMIT_MB`
  - `EASY_MANIM_SANDBOX_TEMP_ROOT`
- if TeX conversion depends on variables such as `TEXMFCNF`, export them **before** starting `easy-manim-mcp` or `easy-manim-worker`; the render subprocess now snapshots that environment from the service process

## Run doctor
```bash
source .venv/bin/activate
easy-manim-doctor --json
```

- In `stub` mode, missing provider credentials do not fail the doctor check.
- In `openai_compatible` mode, add `--strict-provider` or set provider env vars before beta smoke tests.
- For formula-heavy prompts that may use `MathTex` or `Tex`, run `easy-manim-doctor --json --require-latex` before real-provider trials.
- Without `--require-latex`, runtime diagnostics only confirm that `latex` / `dvisvgm` commands are discoverable.
- With `--require-latex`, the doctor performs a small TeX-to-SVG smoke run so it can catch broken LaTeX setups even when both binaries exist on PATH.

## Run tests
```bash
source .venv/bin/activate
python -m pytest -q
```

## Run beta smoke
```bash
source .venv/bin/activate
python scripts/beta_smoke.py --mode ci
```

## Run the MCP server
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport stdio
```

## Optional HTTP transport
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

## HTTP API service
```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-db-bootstrap --data-dir data
easy-manim-api --host 127.0.0.1 --port 8001 --data-dir data --no-embedded-worker
easy-manim-worker --data-dir data
```

- use `easy-manim-agent-admin --data-dir data create-profile ...` and `issue-token ...` before external agent clients log in
- login once through `POST /api/sessions`, then send `Authorization: Bearer <session_token>` on task, memory, profile, and eval requests
- use `GET /api/profile/evals` and `GET /api/profile/evals/<run_id>` to inspect agent-scoped eval summaries over plain HTTP

## Run server and worker separately
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

- restart the server / worker after changing TeX-related environment variables so new render subprocesses inherit the updated values

## Operator utilities
```bash
source .venv/bin/activate
easy-manim-db-bootstrap --data-dir data
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --dry-run
easy-manim-export-task --data-dir data --task-id <task_id> --output /tmp/<task_id>.zip
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag smoke --agent-id agent-a --memory-id mem-1 --profile-patch-json '{"style_hints":{"tone":"teaching"}}' --json
```

## Local execution model
- `FastMCP` server lives in `video_agent.server.fastmcp_server`
- in-process app wiring lives in `video_agent.server.app`
- server startup can run a local background worker loop or skip it for two-process mode
- task logs are written to `data/tasks/<task_id>/logs/events.jsonl`
- artifacts are written under `data/tasks/<task_id>/`
- scene plans are persisted under `data/tasks/<task_id>/artifacts/scene_plan.json`
- worker heartbeats are persisted in SQLite and surfaced through `get_runtime_status`
- `get_runtime_status` now exposes the active sandbox profile, including temp root validity and optional network / process / memory restrictions

## Current limitation
- task storage is still SQLite + local filesystem only; this is beta-ready, not distributed-queue ready.
