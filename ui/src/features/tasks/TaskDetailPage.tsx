import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { cancelTask, getTask, getTaskResult, retryTask, reviseTask, TaskResult, TaskSnapshot } from "../../lib/tasksApi";
import { useSession } from "../auth/useSession";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function TaskDetailPage() {
  const { taskId } = useParams();
  const { sessionToken } = useSession();
  const [snapshot, setSnapshot] = useState<TaskSnapshot | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "revise" | "retry" | "cancel">("idle");

  useEffect(() => {
    if (!taskId) return;
    const id = taskId;
    let cancelled = false;
    let timer: number | null = null;
    let attempt = 0;

    async function loadOnce() {
      if (!sessionToken) return;
      try {
        const s = await getTask(id, sessionToken);
        if (cancelled) return;
        setSnapshot(s);
        const r = await getTaskResult(id, sessionToken);
        if (cancelled) return;
        setResult(r);
        if (!TERMINAL.has(String(s.status))) {
          const delay = Math.min(250 * 2 ** attempt, 5000);
          attempt += 1;
          timer = window.setTimeout(loadOnce, delay);
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
  }, [taskId, sessionToken, reloadTick]);

  async function onRevise() {
    if (!taskId || !sessionToken) return;
    const trimmed = feedback.trim();
    if (!trimmed) return;
    setActionState("revise");
    setActionError(null);
    try {
      await reviseTask(taskId, trimmed, sessionToken);
      setFeedback("");
      setReloadTick((t) => t + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "task_revise_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onRetry() {
    if (!taskId || !sessionToken) return;
    setActionState("retry");
    setActionError(null);
    try {
      await retryTask(taskId, sessionToken);
      setReloadTick((t) => t + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "task_retry_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onCancel() {
    if (!taskId || !sessionToken) return;
    setActionState("cancel");
    setActionError(null);
    try {
      await cancelTask(taskId, sessionToken);
      setReloadTick((t) => t + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "task_cancel_failed");
    } finally {
      setActionState("idle");
    }
  }

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

      <div className="card" style={{ marginTop: 18 }}>
        <div className="cardTitle">Actions</div>
        <div className="muted small">Revise with feedback, retry failures, or cancel in-progress work.</div>

        <label className="field" style={{ marginTop: 10 }}>
          <span className="fieldLabel">Feedback</span>
          <textarea
            aria-label="Feedback"
            className="textarea"
            rows={3}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="e.g. make it blue, slower easing, add labels…"
          />
        </label>

        <div className="buttonRow">
          <button className="button buttonPrimary" type="button" onClick={onRevise} disabled={actionState !== "idle"}>
            {actionState === "revise" ? "Revising…" : "Revise"}
          </button>
          {String(snapshot.status).toLowerCase() === "failed" ? (
            <button className="button" type="button" onClick={onRetry} disabled={actionState !== "idle"}>
              {actionState === "retry" ? "Retrying…" : "Retry"}
            </button>
          ) : null}
          {!TERMINAL.has(String(snapshot.status)) ? (
            <button className="button" type="button" onClick={onCancel} disabled={actionState !== "idle"}>
              {actionState === "cancel" ? "Cancelling…" : "Cancel"}
            </button>
          ) : null}
        </div>

        {actionError ? (
          <p role="alert" className="alert">
            {actionError}
          </p>
        ) : null}
      </div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: "0 0 8px", fontFamily: "var(--font-display)", letterSpacing: "-0.02em" }}>
          Result
        </h3>
        {result ? (
          <div style={{ display: "grid", gap: 8 }}>
            <div className="muted small">Summary</div>
            <div>{String(result.summary ?? "") || <span className="muted">None</span>}</div>
            {result.video_resource ? (
              <a href={result.video_resource} className="muted">
                {result.video_resource.split("/").slice(-1)[0]}
              </a>
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
