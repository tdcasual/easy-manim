import { useEffect, useState } from "react";

import {
  clearSessionMemory,
  disableMemory,
  getSessionMemorySummary,
  listMemories,
  promoteSessionMemory,
  SessionMemorySummary,
  AgentMemoryRecord
} from "../../lib/memoryApi";
import { useSession } from "../auth/useSession";

export function MemoryPage() {
  const { sessionToken } = useSession();
  const [summary, setSummary] = useState<SessionMemorySummary | null>(null);
  const [memories, setMemories] = useState<AgentMemoryRecord[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "clearing" | "promoting" | "disabling">("idle");
  const [actionError, setActionError] = useState<string | null>(null);

  async function refresh() {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const [s, m] = await Promise.all([getSessionMemorySummary(sessionToken), listMemories(sessionToken)]);
      setSummary(s);
      setMemories(Array.isArray(m.items) ? m.items : []);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "memory_load_failed");
    }
  }

  useEffect(() => {
    refresh();
    // refresh is stable for our use.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

  async function onClearSession() {
    if (!sessionToken) return;
    setActionState("clearing");
    setActionError(null);
    try {
      await clearSessionMemory(sessionToken);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "memory_clear_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onPromote() {
    if (!sessionToken) return;
    setActionState("promoting");
    setActionError(null);
    try {
      await promoteSessionMemory(sessionToken);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "memory_promote_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onDisable(memoryId: string) {
    if (!sessionToken) return;
    setActionState("disabling");
    setActionError(null);
    try {
      await disableMemory(memoryId, sessionToken);
      await refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "memory_disable_failed");
    } finally {
      setActionState("idle");
    }
  }

  if (!sessionToken) {
    return (
      <section>
        <h2>Memory</h2>
        <p className="muted">Not authenticated.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Memory</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Session summary and persistent memories.
      </p>

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "memory_load_failed"}
        </p>
      ) : null}

      {actionError ? (
        <p role="alert" className="alert">
          {actionError}
        </p>
      ) : null}

      <div className="tasksGrid" style={{ marginTop: 14 }}>
        <div className="card">
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
            <div className="cardTitle">Session</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                className="button buttonQuiet"
                type="button"
                onClick={onClearSession}
                disabled={actionState !== "idle"}
              >
                {actionState === "clearing" ? "Clearing…" : "Clear session"}
              </button>
              <button
                className="button buttonQuiet"
                type="button"
                onClick={onPromote}
                disabled={actionState !== "idle"}
              >
                {actionState === "promoting" ? "Promoting…" : "Promote to persistent"}
              </button>
            </div>
          </div>
          {summary ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div className="muted small">{summary.entry_count} entr{summary.entry_count === 1 ? "y" : "ies"}</div>
              <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.45 }}>{summary.summary_text || "No summary yet."}</div>
            </div>
          ) : (
            <p className="muted">{status === "loading" ? "Loading…" : "No session summary yet."}</p>
          )}
        </div>

        <div className="card">
          <div className="cardTitle">Persistent</div>
          <div className="muted small">Memories promoted from sessions.</div>
          {memories.length ? (
            <ul className="taskItems">
              {memories.map((m) => (
                <li key={m.memory_id} className="taskItem">
                  <div className="taskLink" style={{ cursor: "default" }}>
                    <span className="taskId">{m.memory_id}</span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span className="taskStatus">{m.status}</span>
                      {String(m.status).toLowerCase() === "active" ? (
                        <button
                          className="button buttonQuiet"
                          type="button"
                          onClick={() => onDisable(m.memory_id)}
                          disabled={actionState !== "idle"}
                        >
                          Disable
                        </button>
                      ) : null}
                    </span>
                  </div>
                  <div style={{ padding: "0 12px 12px" }} className="muted small">
                    {m.summary_text}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted" style={{ marginTop: 12 }}>
              No persistent memories yet.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
