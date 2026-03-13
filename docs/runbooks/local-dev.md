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
easy-manim-mcp --transport stdio
```

## Optional HTTP transport
```bash
source .venv/bin/activate
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

## Run server and worker separately
```bash
source .venv/bin/activate
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

- restart the server / worker after changing TeX-related environment variables so new render subprocesses inherit the updated values

## Operator utilities
```bash
source .venv/bin/activate
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --dry-run
easy-manim-export-task --data-dir data --task-id <task_id> --output /tmp/<task_id>.zip
```

## Local execution model
- `FastMCP` server lives in `video_agent.server.fastmcp_server`
- in-process app wiring lives in `video_agent.server.app`
- server startup can run a local background worker loop or skip it for two-process mode
- task logs are written to `data/tasks/<task_id>/logs/events.jsonl`
- artifacts are written under `data/tasks/<task_id>/`
- worker heartbeats are persisted in SQLite and surfaced through `get_runtime_status`

## Current limitation
- task storage is still SQLite + local filesystem only; this is beta-ready, not distributed-queue ready.
