# Real Provider Trial Runbook

## Goal
Run the curated `real-provider` subset from `evals/beta_prompt_suite.json`, collect the generated evaluation artifacts, export a reviewer-ready qa bundle, and record a release decision.

## Choose the RC subset
- The release-candidate subset is defined by the `real-provider` tag in `evals/beta_prompt_suite.json`.
- Keep the deterministic smoke subset for CI with `--include-tag smoke`.
- Keep the deterministic repair subset for CI / preflight with `--include-tag repair`.
- Use the real-provider subset only in a manually supervised environment with real credentials.

## Prepare the environment
```bash
source .venv/bin/activate
cp .env.beta.example .env.beta
set -a
source .env.beta
set +a
python -m pip install -e '.[dev]'
```

Required variables in `.env.beta`:
- `EASY_MANIM_LLM_PROVIDER=litellm`
- `EASY_MANIM_LLM_MODEL=<litellm-model-route>`
- `EASY_MANIM_LLM_API_BASE=<provider-base-url>`
- `EASY_MANIM_LLM_API_KEY=<provider-api-key>`
- `EASY_MANIM_RELEASE_CHANNEL=rc`
- `EASY_MANIM_AUTO_REPAIR_ENABLED=true`

If the selected prompts may render formulas with `MathTex` / `Tex`, also ensure:
- `latex` is available on PATH, or `EASY_MANIM_LATEX_COMMAND` points to it
- `dvisvgm` is available on PATH, or `EASY_MANIM_DVISVGM_COMMAND` points to it
- any required `TEXMF*` environment variables are exported in the shell **before** launching the MCP server or worker, so the render subprocess inherits them

Before any standalone `easy-manim-eval-run`, `easy-manim-agent-admin`, `easy-manim-api`, `easy-manim-mcp`, or `easy-manim-worker` command below, bootstrap the local SQLite database once with `easy-manim-db-bootstrap --data-dir data`.

## Preflight
```bash
source .venv/bin/activate
easy-manim-doctor --json --require-latex
python scripts/release_candidate_gate.py --mode ci
easy-manim-db-bootstrap --data-dir data
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag repair --json
```

## Run the real-provider evaluation
```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag real-provider --json
```

If the run is interrupted after emitting a `run_id`, resume the same slice without duplicating already completed cases:

```bash
source .venv/bin/activate
easy-manim-eval-run \
  --data-dir data \
  --suite evals/beta_prompt_suite.json \
  --include-tag real-provider \
  --resume-run-id <run_id> \
  --json
```

If you intentionally want to re-run one completed case inside the same eval record, add `--rerun-case <case_id>`.

To isolate only the quality-sensitive real-provider prompts, run the tag intersection slice:

```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag real-provider --include-tag quality --match-all-tags --json
```

If you want the trial to target a specific named agent baseline, add the agent-aware flags:

```bash
source .venv/bin/activate
easy-manim-eval-run \
  --data-dir data \
  --suite evals/beta_prompt_suite.json \
  --include-tag real-provider \
  --agent-id agent-a \
  --memory-id mem-1 \
  --profile-patch-json '{"style_hints":{"tone":"teaching"}}' \
  --json
```

## Collect evidence
After the run completes, record the emitted `run_id` and collect:
- `data/evals/<run_id>/summary.json`
- `data/evals/<run_id>/summary.md`
- `data/evals/<run_id>/review_digest.md`
- `data/evals/<run_id>/run_manifest.json`
- a qa bundle exported with:

```bash
source .venv/bin/activate
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

The qa bundle should contain the run summary plus task-local artifacts under `tasks/<task_id>/` for reviewer inspection.

For agent-targeted trials, also confirm `summary.json.report.agent` is present and that the active profile digest matches the intended baseline.

## Evaluate the live gate
Run the manual live-provider gate against the quality-sensitive real-provider run:

```bash
source .venv/bin/activate
python scripts/live_provider_gate.py --summary data/evals/<run_id>/summary.json
```

To compare against the previously approved live baseline:

```bash
source .venv/bin/activate
python scripts/live_provider_gate.py \
  --summary data/evals/<run_id>/summary.json \
  --baseline-summary data/evals/<previous_run_id>/summary.json
```

The gate evaluates:
- overall live pass rate
- formula-specific live pass rate
- risk-domain failure regressions versus the prior approved summary

## Operator review notes
Capture the following during review:
- prompts that failed or regressed
- items listed in `review_digest.md`
- top failure codes from `summary.json`
- top risk-domain failure counts from `summary.json.report.live`
- repair attempt / success rates from the deterministic repair slice
- render quality issues not caught by validators
- provider-specific latency or reliability observations
- whether any issues block beta-to-RC promotion

## Record the decision
Copy `docs/templates/release-candidate-decision.md` and fill in:
- build identifier
- suite and run ID
- pass rate and major failure codes
- reviewer names and date
- go / conditional go / no-go decision
