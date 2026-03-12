# Real Provider Trial Runbook

## Goal
Run the curated `real-provider` subset from `evals/beta_prompt_suite.json`, collect the generated evaluation artifacts, export a reviewer-ready qa bundle, and record a release decision.

## Choose the RC subset
- The release-candidate subset is defined by the `real-provider` tag in `evals/beta_prompt_suite.json`.
- Keep the deterministic smoke subset for CI with `--include-tag smoke`.
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
- `EASY_MANIM_LLM_PROVIDER=openai_compatible`
- `EASY_MANIM_LLM_MODEL=<real-model>`
- `EASY_MANIM_LLM_BASE_URL=<provider-base-url>`
- `EASY_MANIM_LLM_API_KEY=<provider-api-key>`
- `EASY_MANIM_RELEASE_CHANNEL=rc`

## Preflight
```bash
source .venv/bin/activate
easy-manim-doctor --json
python scripts/release_candidate_gate.py --mode ci
```

## Run the real-provider evaluation
```bash
source .venv/bin/activate
easy-manim-eval-run --data-dir data --suite evals/beta_prompt_suite.json --include-tag real-provider --json
```

## Collect evidence
After the run completes, record the emitted `run_id` and collect:
- `data/evals/<run_id>/summary.json`
- `data/evals/<run_id>/summary.md`
- a qa bundle exported with:

```bash
source .venv/bin/activate
easy-manim-qa-bundle --data-dir data --run-id <run_id> --output /tmp/<run_id>-qa-bundle.zip
```

The qa bundle should contain the run summary plus task-local artifacts under `tasks/<task_id>/` for reviewer inspection.

## Operator review notes
Capture the following during review:
- prompts that failed or regressed
- top failure codes from `summary.json`
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
