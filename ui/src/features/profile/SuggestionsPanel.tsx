import { useEffect, useState } from "react";

import {
  AgentProfileSuggestion,
  applySuggestion,
  dismissSuggestion,
  generateSuggestions,
  listSuggestions
} from "../../lib/suggestionsApi";
import { useSession } from "../auth/useSession";

function safeOneLine(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

export function SuggestionsPanel() {
  const { sessionToken } = useSession();
  const [items, setItems] = useState<AgentProfileSuggestion[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "generating" | "applying" | "dismissing">("idle");

  async function refresh() {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const response = await listSuggestions(sessionToken);
      setItems(Array.isArray(response.items) ? response.items : []);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "suggestions_load_failed");
    }
  }

  useEffect(() => {
    refresh();
    // refresh is stable for our use.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

  async function onGenerate() {
    if (!sessionToken) return;
    setActionState("generating");
    setError(null);
    try {
      const response = await generateSuggestions(sessionToken);
      setItems(Array.isArray(response.items) ? response.items : []);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "suggestions_generate_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onApply(suggestionId: string) {
    if (!sessionToken) return;
    setActionState("applying");
    setError(null);
    try {
      await applySuggestion(suggestionId, sessionToken);
      await refresh();
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "suggestion_apply_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onDismiss(suggestionId: string) {
    if (!sessionToken) return;
    setActionState("dismissing");
    setError(null);
    try {
      await dismissSuggestion(suggestionId, sessionToken);
      await refresh();
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "suggestion_dismiss_failed");
    } finally {
      setActionState("idle");
    }
  }

  if (!sessionToken) {
    return <p className="muted">Not authenticated.</p>;
  }

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
        <div className="cardTitle" style={{ marginBottom: 0 }}>
          Suggestions
        </div>
        <button className="button buttonQuiet" type="button" onClick={onGenerate} disabled={actionState !== "idle"}>
          {actionState === "generating" ? "Generating…" : "Generate suggestions"}
        </button>
      </div>
      <div className="muted small" style={{ marginTop: 6 }}>
        Review proposed profile patches, then apply or dismiss.
      </div>

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "suggestions_load_failed"}
        </p>
      ) : null}

      {status === "loading" && items.length === 0 ? <p className="muted">Loading…</p> : null}

      {items.length ? (
        <ul className="taskItems" style={{ marginTop: 12 }}>
          {items.map((s) => (
            <li key={s.suggestion_id} className="taskItem">
              <div className="taskLink" style={{ cursor: "default" }}>
                <span className="taskId">{s.suggestion_id}</span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                  <span className="taskStatus">{s.status}</span>
                  {String(s.status).toLowerCase() === "pending" ? (
                    <>
                      <button
                        className="button buttonQuiet"
                        type="button"
                        onClick={() => onApply(s.suggestion_id)}
                        disabled={actionState !== "idle"}
                      >
                        Apply
                      </button>
                      <button
                        className="button buttonQuiet"
                        type="button"
                        onClick={() => onDismiss(s.suggestion_id)}
                        disabled={actionState !== "idle"}
                      >
                        Dismiss
                      </button>
                    </>
                  ) : null}
                </span>
              </div>
              <div style={{ padding: "0 12px 12px" }} className="muted small">
                <div>Patch: {safeOneLine(s.patch_json)}</div>
                {Object.keys(s.rationale_json || {}).length ? <div>Rationale: {safeOneLine(s.rationale_json)}</div> : null}
              </div>
            </li>
          ))}
        </ul>
      ) : status === "loading" ? null : (
        <p className="muted" style={{ marginTop: 10 }}>
          No suggestions yet.
        </p>
      )}
    </div>
  );
}

