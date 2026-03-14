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
easy-manim-mcp --transport stdio
```

## Run server and worker separately
```bash
source .venv/bin/activate
easy-manim-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
easy-manim-worker --data-dir data
```

## Run deterministic evaluations
```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag smoke --json
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

Evaluation artifacts are written under `data/evals/<run_id>/` and include `summary.json`, `summary.md`, and `review_digest.md`.

## Release-candidate flow
```bash
source .venv/bin/activate
cp .env.beta.example .env.beta
python scripts/release_candidate_gate.py --mode ci
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag real-provider --json
python scripts/live_provider_gate.py --summary data/evals/<run_id>/summary.json
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

Use `docs/runbooks/real-provider-trial.md` for the trial procedure and `docs/templates/release-candidate-decision.md` to record the go / no-go decision.
If the real-provider prompts may render formulas, make sure `latex` and `dvisvgm` are available first.

## Inspect and maintain beta data
```bash
source .venv/bin/activate
easy-manim-cleanup --data-dir data --older-than-hours 24 --status completed --dry-run
easy-manim-export-task --data-dir data --task-id <task_id> --output /tmp/<task_id>.zip
```

## Container workflow
```bash
docker compose up --build
```

## Important paths
- Phase 2 plan: `docs/plans/2026-03-12-phase-2-beta-readiness-implementation-plan.md`
- Phase 3 plan: `docs/plans/2026-03-12-phase-3-beta-trial-hardening-implementation-plan.md`
- Phase 4 plan: `docs/plans/2026-03-12-phase-4-real-beta-validation-and-release-candidate-implementation-plan.md`
- Local dev guide: `docs/runbooks/local-dev.md`
- Beta ops guide: `docs/runbooks/beta-ops.md`
- Real-provider trial guide: `docs/runbooks/real-provider-trial.md`
- Release checklist: `docs/runbooks/release-checklist.md`
- RC decision template: `docs/templates/release-candidate-decision.md`
- Incident response: `docs/runbooks/incident-response.md`
