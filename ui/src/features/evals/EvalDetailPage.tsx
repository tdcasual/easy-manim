import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getEval, EvalRunSummary } from "../../lib/evalsApi";
import { useSession } from "../auth/useSession";

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

export function EvalDetailPage() {
  const { runId } = useParams();
  const { sessionToken } = useSession();
  const [run, setRun] = useState<EvalRunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || !sessionToken) return;
    let cancelled = false;
    setError(null);
    getEval(runId, sessionToken)
      .then((r) => {
        if (cancelled) return;
        setRun(r);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "eval_load_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [runId, sessionToken]);

  if (!runId) {
    return (
      <section>
        <h2>Eval</h2>
        <p className="muted">Missing run id.</p>
      </section>
    );
  }

  if (!sessionToken) {
    return (
      <section>
        <h2>Eval</h2>
        <p className="muted">Not authenticated.</p>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h2>Eval</h2>
        <p className="muted">Error: {error}</p>
      </section>
    );
  }

  if (!run) {
    return (
      <section>
        <h2>Eval</h2>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  const cases = Array.isArray(run.items) ? run.items : [];

  return (
    <section>
      <header className="sectionHeader">
        <div>
          <h2>Eval</h2>
          <p className="muted" style={{ margin: 0 }}>
            {run.run_id}
          </p>
        </div>
        <Link className="button buttonQuiet" to="/evals">
          Back
        </Link>
      </header>

      <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 12px", margin: "0 0 16px" }}>
        <dt className="muted">Suite</dt>
        <dd style={{ margin: 0 }}>{run.suite_id}</dd>
        <dt className="muted">Provider</dt>
        <dd style={{ margin: 0 }}>{run.provider}</dd>
        <dt className="muted">Cases</dt>
        <dd style={{ margin: 0 }}>{run.total_cases}</dd>
      </dl>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="cardTitle">Cases</div>
        <div className="muted small">Per-case outcomes captured during the run.</div>
        {cases.length ? (
          <ul className="taskItems" style={{ marginTop: 12 }}>
            {cases.map((c) => {
              const status = String(c.status || "").toLowerCase();
              const statusClass = status ? `taskStatus taskStatus_${status}` : "taskStatus";
              const issueCodes = Array.isArray(c.issue_codes) ? c.issue_codes : [];
              const quality = typeof c.quality_score === "number" ? c.quality_score : null;
              const secs = typeof c.duration_seconds === "number" ? c.duration_seconds : null;
              return (
                <li key={`${c.task_id}:${c.root_task_id}`} className="taskItem">
                  <div className="taskLink" style={{ cursor: "default" }}>
                    <span className="taskId">{c.task_id}</span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      {c.manual_review_required ? <span className="taskStatus">review</span> : null}
                      <span className={statusClass}>{c.status}</span>
                    </span>
                  </div>
                  <div style={{ padding: "0 12px 12px" }} className="muted small">
                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                      {secs !== null ? <span>{secs.toFixed(1)}s</span> : null}
                      {quality !== null ? <span>q={quality.toFixed(2)}</span> : null}
                      {issueCodes.length ? <span>issues: {issueCodes.join(", ")}</span> : <span>issues: none</span>}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted" style={{ marginTop: 12 }}>
            No case results in this run payload.
          </p>
        )}
      </div>

      <div className="card">
        <div className="cardTitle">Report</div>
        <pre
          style={{
            margin: 0,
            padding: 12,
            borderRadius: 12,
            border: "1px solid color-mix(in oklab, var(--hairline), transparent 22%)",
            background: "color-mix(in oklab, var(--surface), transparent 4%)",
            overflow: "auto",
            maxHeight: 360,
            lineHeight: 1.35,
            fontSize: 12
          }}
        >
          {safeStringify(run.report ?? {})}
        </pre>
      </div>
    </section>
  );
}
