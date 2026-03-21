import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EvalRunSummary, listEvals } from "../../lib/evalsApi";
import { useSession } from "../auth/useSession";

function readSuccessRate(report?: Record<string, unknown>): number | null {
  const raw = report?.success_rate;
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function EvalsPage() {
  const { sessionToken } = useSession();
  const [items, setItems] = useState<EvalRunSummary[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionToken) return;
    let cancelled = false;
    setStatus("loading");
    setError(null);
    listEvals(sessionToken)
      .then((response) => {
        if (cancelled) return;
        setItems(Array.isArray(response.items) ? response.items : []);
        setStatus("idle");
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setError(err instanceof Error ? err.message : "evals_load_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionToken]);

  if (!sessionToken) {
    return (
      <section>
        <h2>Evals</h2>
        <p className="muted">Not authenticated.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Evals</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Agent-scoped evaluation runs.
      </p>

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "evals_load_failed"}
        </p>
      ) : null}

      {status === "loading" && items.length === 0 ? <p className="muted">Loading…</p> : null}

      {items.length ? (
        <ul className="taskItems" aria-label="eval run list">
          {items.map((run) => {
            const rate = readSuccessRate(run.report);
            const badge = rate === null ? null : `${Math.round(rate * 100)}%`;
            return (
              <li key={run.run_id} className="taskItem">
                <Link className="taskLink" to={`/evals/${encodeURIComponent(run.run_id)}`}>
                  <span className="taskId">{run.run_id}</span>
                  <span className="taskStatus">{badge ?? `${run.total_cases} cases`}</span>
                </Link>
                <div style={{ padding: "0 12px 12px" }} className="muted small">
                  <span>{run.suite_id}</span>
                  <span style={{ padding: "0 10px", opacity: 0.6 }} aria-hidden="true">
                    ·
                  </span>
                  <span>{run.provider}</span>
                </div>
              </li>
            );
          })}
        </ul>
      ) : status === "loading" ? null : (
        <p className="muted">No eval runs yet.</p>
      )}
    </section>
  );
}

