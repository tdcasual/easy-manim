import { useEffect, useState } from "react";

import { EmptyState, SectionPanel, StatusPill } from "../../app/ui";
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
    return <p className="muted">当前未登录。</p>;
  }

  return (
    <SectionPanel
      title="建议"
      detail="查看系统生成的画像补丁建议，并决定是否显式应用或忽略。"
      actions={
        <button className="button buttonQuiet" type="button" onClick={onGenerate} disabled={actionState !== "idle"}>
          {actionState === "generating" ? "正在生成…" : "生成建议"}
        </button>
      }
      className="sectionPanel--list"
    >
      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "suggestions_load_failed"}
        </p>
      ) : null}

      {status === "loading" && items.length === 0 ? <p className="muted">正在加载…</p> : null}

      {items.length ? (
        <ul className="listStack">
          {items.map((suggestion) => (
            <li key={suggestion.suggestion_id} className="listStaticRow">
              <div className="listPrimary">
                <div className="listTitleRow">
                  <span className="listTitle">{suggestion.suggestion_id}</span>
                  <StatusPill value={suggestion.status} compact />
                </div>
                <p className="listCaption">补丁：{safeOneLine(suggestion.patch_json)}</p>
                {Object.keys(suggestion.rationale_json || {}).length ? (
                  <p className="listCaption">原因：{safeOneLine(suggestion.rationale_json)}</p>
                ) : null}
              </div>
              <div className="listMeta">
                {String(suggestion.status).toLowerCase() === "pending" ? (
                  <div className="inlineActions">
                    <button
                      className="button buttonQuiet"
                      type="button"
                      onClick={() => onApply(suggestion.suggestion_id)}
                      disabled={actionState !== "idle"}
                    >
                      应用
                    </button>
                    <button
                      className="button buttonQuiet"
                      type="button"
                      onClick={() => onDismiss(suggestion.suggestion_id)}
                      disabled={actionState !== "idle"}
                    >
                      忽略
                    </button>
                  </div>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : status === "loading" ? null : (
        <EmptyState
          title="还没有建议"
          body="等智能体再多积累一些任务、记忆或评测历史后，再生成一批建议会更有价值。"
        />
      )}
    </SectionPanel>
  );
}
