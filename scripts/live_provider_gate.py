from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate_live_gate(
    summary: dict,
    *,
    min_live_pass_rate: float,
    min_formula_pass_rate: float,
    max_risk_regression: int,
    baseline: dict | None = None,
) -> dict[str, object]:
    reasons: list[str] = []
    live = summary.get("report", {}).get("live", {})
    pass_rate = float(live.get("pass_rate", 0.0))
    formula_pass_rate = float(live.get("formula_pass_rate", 0.0))
    if pass_rate < min_live_pass_rate:
        reasons.append(f"live_pass_rate {pass_rate:.2f} below threshold {min_live_pass_rate:.2f}")
    if formula_pass_rate < min_formula_pass_rate:
        reasons.append(f"formula_pass_rate {formula_pass_rate:.2f} below threshold {min_formula_pass_rate:.2f}")

    if baseline is not None:
        current_counts = live.get("risk_domain_failure_counts", {})
        baseline_counts = baseline.get("report", {}).get("live", {}).get("risk_domain_failure_counts", {})
        for domain, current_value in current_counts.items():
            previous_value = int(baseline_counts.get(domain, 0))
            if int(current_value) - previous_value > max_risk_regression:
                reasons.append(f"risk_domain {domain} regressed from {previous_value} to {current_value}")

    return {"ok": not reasons, "reasons": reasons}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a manual live-provider run")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--baseline-summary", type=Path)
    parser.add_argument("--min-live-pass-rate", type=float, default=0.8)
    parser.add_argument("--min-formula-pass-rate", type=float, default=0.8)
    parser.add_argument("--max-risk-regression", type=int, default=0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = json.loads(args.summary.read_text())
    baseline = json.loads(args.baseline_summary.read_text()) if args.baseline_summary else None
    payload = evaluate_live_gate(
        summary,
        min_live_pass_rate=args.min_live_pass_rate,
        min_formula_pass_rate=args.min_formula_pass_rate,
        max_risk_regression=args.max_risk_regression,
        baseline=baseline,
    )
    print(json.dumps(payload))
    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
