import { useEffect, useState } from "react";

import { EmptyState, MetricChip, PageIntro, SectionPanel, StatusPill } from "../../app/ui";
import {
  AgentMemoryRecord,
  clearSessionMemory,
  disableMemory,
  getSessionMemorySummary,
  listMemories,
  promoteSessionMemory,
  SessionMemorySummary
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
      const [nextSummary, nextMemories] = await Promise.all([getSessionMemorySummary(sessionToken), listMemories(sessionToken)]);
      setSummary(nextSummary);
      setMemories(Array.isArray(nextMemories.items) ? nextMemories.items : []);
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
      <section className="page">
        <h2>记忆</h2>
        <p className="muted">当前未登录。</p>
      </section>
    );
  }

  const activeMemories = memories.filter((memory) => String(memory.status).toLowerCase() === "active").length;
  const disabledMemories = memories.filter((memory) => String(memory.status).toLowerCase() !== "active").length;

  return (
    <section className="page">
      <PageIntro
        eyebrow="连续性"
        title="记忆"
        description="把当前会话里的有效经验整理清楚，再把值得保留的部分提升为长期记忆，帮助后续任务从更好的上下文开始。"
        actions={
          <button className="button buttonQuiet" type="button" onClick={refresh} disabled={status === "loading"}>
            {status === "loading" ? "正在刷新…" : "刷新"}
          </button>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="会话条目" value={summary?.entry_count ?? 0} />
            <MetricChip label="启用记忆" value={activeMemories} />
            <MetricChip label="已停用" value={disabledMemories} />
          </div>
        }
      />

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

      <div className="pageSplit">
        <SectionPanel
          title="会话记忆"
          detail="这里汇总当前工作会话中的临时经验。上下文过时可以清空，判断有价值时可以提升为长期记忆。"
          actions={
            <div className="inlineActions">
              <button className="button buttonQuiet" type="button" onClick={onClearSession} disabled={actionState !== "idle"}>
                {actionState === "clearing" ? "正在清空…" : "清空会话"}
              </button>
              <button className="button buttonPrimary" type="button" onClick={onPromote} disabled={actionState !== "idle"}>
                {actionState === "promoting" ? "正在提升…" : "提升为长期记忆"}
              </button>
            </div>
          }
        >
          {summary ? (
            <div className="resultStack">
              <div className="infoBlock">
                <span className="infoLabel">摘要</span>
                <p className="infoValue">{summary.summary_text || "暂时还没有会话摘要。"}</p>
              </div>
              <div className="metaChips">
                <span className="metaChip">条目 {summary.entry_count}</span>
                {summary.summary_digest ? <span className="metaChip">摘要指纹 {summary.summary_digest}</span> : null}
                {summary.lineage_refs?.length ? <span className="metaChip">来源链路 {summary.lineage_refs.length}</span> : null}
              </div>
            </div>
          ) : (
            <EmptyState
              title={status === "loading" ? "正在加载会话记忆" : "还没有会话摘要"}
              body="先创建或修订几个任务。只有当智能体有了连续的工作轨迹，会话记忆才会真正变得有用。"
            />
          )}
        </SectionPanel>

        <SectionPanel
          title="长期记忆"
          detail="提升后的记忆会继续附着在当前智能体上；当它不再有帮助时，也可以随时停用。"
          className="sectionPanel--list"
        >
          {memories.length ? (
            <ul className="listStack">
              {memories.map((memory) => (
                <li key={memory.memory_id} className="listStaticRow">
                  <div className="listPrimary">
                    <div className="listTitleRow">
                      <span className="listTitle">{memory.memory_id}</span>
                      <StatusPill value={memory.status} compact />
                    </div>
                    <p className="listCaption">{memory.summary_text}</p>
                  </div>
                  <div className="listMeta listMeta--column">
                    <span className="muted small">来源会话：{memory.source_session_id}</span>
                    {String(memory.status).toLowerCase() === "active" ? (
                      <button
                        className="button buttonQuiet"
                        type="button"
                        onClick={() => onDisable(memory.memory_id)}
                        disabled={actionState !== "idle"}
                      >
                        停用
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="还没有长期记忆"
              body="当会话摘要已经体现出可复用的偏好或流程习惯时，再把它提升为长期记忆会更合适。"
            />
          )}
        </SectionPanel>
      </div>
    </section>
  );
}
