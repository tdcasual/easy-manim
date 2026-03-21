import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getTask, getTaskResult, TaskResult, TaskSnapshot } from "../../lib/tasksApi";
import { useSession } from "../auth/useSession";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function TaskDetailPage() {
  const { taskId } = useParams();
  const { sessionToken } = useSession();
  const [snapshot, setSnapshot] = useState<TaskSnapshot | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    let timer: number | null = null;

    async function loadOnce() {
      if (!sessionToken) return;
      try {
        const s = await getTask(taskId, sessionToken);
        if (cancelled) return;
        setSnapshot(s);
        const r = await getTaskResult(taskId, sessionToken);
        if (cancelled) return;
        setResult(r);
        if (!TERMINAL.has(String(s.status))) {
          timer = window.setTimeout(loadOnce, 200);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "task_load_failed");
      }
    }

    loadOnce();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [taskId, sessionToken]);

  if (!taskId) {
    return (
      <section>
        <h2>Task</h2>
        <p className="muted">Missing task id.</p>
      </section>
    );
  }

  if (error) {
    return (
      <section>
        <h2>Task</h2>
        <p className="muted">Error: {error}</p>
      </section>
    );
  }

  if (!snapshot) {
    return (
      <section>
        <h2>Task</h2>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  return (
    <section>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16 }}>
        <h2>Task</h2>
        <span className="muted small">{snapshot.task_id}</span>
      </div>

      <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 12px", margin: "16px 0 0" }}>
        <dt className="muted">Status</dt>
        <dd style={{ margin: 0 }}>{String(snapshot.status)}</dd>
        <dt className="muted">Phase</dt>
        <dd style={{ margin: 0 }}>{String(snapshot.phase)}</dd>
        <dt className="muted">Attempts</dt>
        <dd style={{ margin: 0 }}>{String(snapshot.attempt_count ?? 0)}</dd>
      </dl>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: "0 0 8px", fontFamily: "var(--font-display)", letterSpacing: "-0.02em" }}>
          Result
        </h3>
        {result ? (
          <div style={{ display: "grid", gap: 8 }}>
            <div className="muted small">Summary</div>
            <div>{String(result.summary ?? "") || <span className="muted">None</span>}</div>
            {result.video_resource ? (
              <Link to={result.video_resource} className="muted">
                {result.video_resource.split("/").slice(-1)[0]}
              </Link>
            ) : (
              <span className="muted">No video resource yet.</span>
            )}
          </div>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </div>
    </section>
  );
}

