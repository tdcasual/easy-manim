import { useEffect, useState, useCallback } from "react";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import {
  Brain,
  RefreshCw,
  Trash2,
  ArrowUp,
  Loader2,
  AlertCircle,
  Lightbulb,
  Search,
} from "lucide-react";
import { useSession } from "../auth/useSession";
import {
  AgentMemoryRecord,
  clearSessionMemory,
  disableMemory,
  getSessionMemorySummary,
  listMemories,
  MemoryRetrievalHit,
  promoteSessionMemory,
  retrieveMemories,
  SessionMemorySummary,
} from "../../lib/memoryApi";
import { useI18n } from "../../app/locale";
import { SkeletonMetricCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/useARIAMessage";
import { useConfirm } from "../../components/useConfirm";
import { getStatusLabel } from "../../app/ui";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import "./MemoryPageV2.css";

export function MemoryPageV2() {
  const { sessionToken } = useSession();
  const { locale, t } = useI18n();
  const { showAuthModal, closeAuthModal } = useAuthGuard();
  const [summary, setSummary] = useState<SessionMemorySummary | null>(null);
  const [memories, setMemories] = useState<AgentMemoryRecord[]>([]);
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [retrievalHits, setRetrievalHits] = useState<MemoryRetrievalHit[]>([]);
  const [retrievalState, setRetrievalState] = useState<"idle" | "searching">("idle");
  const { status, error, startLoading, setErrorState, succeed } = useAsyncStatus();
  const [actionState, setActionState] = useState<"idle" | "clearing" | "promoting" | "disabling">(
    "idle"
  );
  const [actionError, setActionError] = useState<string | null>(null);
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  const { confirm, ConfirmDialog } = useConfirm();

  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    startLoading();
    try {
      const [nextSummary, nextMemories] = await Promise.all([
        getSessionMemorySummary(sessionToken),
        listMemories(sessionToken),
      ]);
      setSummary(nextSummary);
      setMemories(Array.isArray(nextMemories.items) ? nextMemories.items : []);
      succeed();
    } catch (err) {
      setErrorState(err instanceof Error ? err.message : t("common.loadingFailed"));
    }
  }, [sessionToken, t, startLoading, succeed, setErrorState]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleClear = useCallback(async () => {
    if (!sessionToken) return;

    // 显示确认对话框
    const confirmed = await confirm({
      title: t("memory.clearConfirmTitle"),
      message: t("memory.clearConfirmMessage"),
      confirmText: t("memory.clearConfirmAction"),
      cancelText: t("common.cancel"),
      danger: true,
    });

    if (!confirmed) return;

    setActionState("clearing");
    setActionError(null);
    try {
      await clearSessionMemory(sessionToken);
      await refresh();
      announcePolite(t("memory.cleared"));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("memory.clear");
      setActionError(errorMsg);
      announcePolite(t("memory.clearFailed", { error: errorMsg }));
    } finally {
      setActionState("idle");
    }
  }, [sessionToken, refresh, confirm, announcePolite, t]);

  const handlePromote = useCallback(async () => {
    if (!sessionToken) return;

    // 显示确认对话框
    const confirmed = await confirm({
      title: t("memory.promoteConfirmTitle"),
      message: t("memory.promoteConfirmMessage"),
      confirmText: t("memory.promoteConfirmAction"),
      cancelText: t("common.cancel"),
      danger: false,
    });

    if (!confirmed) return;

    setActionState("promoting");
    setActionError(null);
    try {
      await promoteSessionMemory(sessionToken);
      await refresh();
      announcePolite(t("memory.promoted"));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("memory.promote");
      setActionError(errorMsg);
      announcePolite(t("memory.promoteFailed", { error: errorMsg }));
    } finally {
      setActionState("idle");
    }
  }, [sessionToken, refresh, confirm, announcePolite, t]);

  const handleDisable = useCallback(
    async (memoryId: string) => {
      if (!sessionToken) return;

      // 显示确认对话框
      const confirmed = await confirm({
        title: t("memory.disableConfirmTitle"),
        message: t("memory.disableConfirmMessage", { memoryId: `${memoryId.slice(0, 8)}...` }),
        confirmText: t("memory.disableConfirmAction"),
        cancelText: t("common.cancel"),
        danger: true,
      });

      if (!confirmed) return;

      setActionState("disabling");
      setActionError(null);
      try {
        await disableMemory(memoryId, sessionToken);
        await refresh();
        announcePolite(t("memory.disabled"));
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : t("memory.disable");
        setActionError(errorMsg);
        announcePolite(t("memory.disableFailed", { error: errorMsg }));
      } finally {
        setActionState("idle");
      }
    },
    [sessionToken, refresh, confirm, announcePolite, t]
  );

  const handleRetrieve = useCallback(async () => {
    if (!sessionToken || !retrievalQuery.trim()) return;

    setRetrievalState("searching");
    setActionError(null);
    try {
      const payload = await retrieveMemories(retrievalQuery.trim(), sessionToken);
      setRetrievalHits(Array.isArray(payload.items) ? payload.items : []);
      announcePolite(
        `Retrieved ${Array.isArray(payload.items) ? payload.items.length : 0} memory diagnostics`
      );
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "memory_retrieval_failed";
      setActionError(errorMsg);
      announcePolite(`Memory retrieval failed: ${errorMsg}`);
    } finally {
      setRetrievalState("idle");
    }
  }, [announcePolite, retrievalQuery, sessionToken]);

  const activeCount = memories.filter((m) => m.status.toLowerCase() === "active").length;

  if (!sessionToken) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">
          <p>{t("common.notLoggedIn")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-v2">
      {/* ARIA Live 区域 */}
      <ARIALiveRegion />

      {/* 确认对话框 */}
      <ConfirmDialog />

      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">{t("memory.page.eyebrow")}</div>
          <h1 className="page-title-v2">{t("memory.page.title")}</h1>
          <p className="page-description-v2">{t("memory.page.description")}</p>
        </div>
        <button
          className="refresh-btn"
          onClick={refresh}
          disabled={status === "loading"}
          aria-busy={status === "loading"}
        >
          {status === "loading" ? <Loader2 size={18} className="spin" /> : <RefreshCw size={18} />}
          {t("memory.refresh")}
        </button>
      </div>

      {error && (
        <div className="form-error-v2" role="alert">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {actionError && (
        <div className="form-error-v2" role="alert">
          <AlertCircle size={16} />
          {actionError}
        </div>
      )}

      {status === "loading" && !summary ? (
        <div className="metrics-grid-v2">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : (
        <div className="metrics-grid-v2">
          <div
            className="metric-card-v2"
            style={{ "--card-color": "var(--accent-pink)" } as React.CSSProperties}
          >
            <div
              className="metric-icon-wrapper"
              style={{ background: "rgba(236, 72, 153, 0.15)", color: "var(--accent-pink)" }}
            >
              <Brain size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">{t("memory.sessionEntries")}</p>
              <h3 className="metric-value-v2">{summary?.entry_count ?? 0}</h3>
            </div>
          </div>
          <div
            className="metric-card-v2"
            style={{ "--card-color": "var(--success)" } as React.CSSProperties}
          >
            <div
              className="metric-icon-wrapper"
              style={{ background: "rgba(16, 185, 129, 0.15)", color: "var(--success)" }}
            >
              <Brain size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">{t("memory.activeMemories")}</p>
              <h3 className="metric-value-v2">{activeCount}</h3>
            </div>
          </div>
        </div>
      )}

      <div className="content-grid-v2 single-column">
        <div className="section-card-v2">
          <div className="section-header-v2">
            <h3 className="section-title-v2">
              <Brain size={20} />
              {t("memory.sessionMemory")}
            </h3>
            <div className="memory-actions">
              <button
                type="button"
                className="action-btn danger"
                onClick={handleClear}
                disabled={actionState !== "idle"}
                aria-busy={actionState === "clearing"}
              >
                <Trash2 size={16} />
                {actionState === "clearing" ? t("memory.clearing") : t("memory.clear")}
              </button>
              <button
                type="button"
                className="action-btn primary"
                onClick={handlePromote}
                disabled={actionState !== "idle"}
                aria-busy={actionState === "promoting"}
              >
                <ArrowUp size={16} />
                {actionState === "promoting" ? t("memory.promoting") : t("memory.promote")}
              </button>
            </div>
          </div>

          {status === "loading" && !summary ? (
            <div className="loading-state-v2">
              <Loader2 size={24} className="spin" />
              <p>{t("memory.loading")}</p>
            </div>
          ) : summary ? (
            <div className="memory-content">
              <p className="memory-summary">{summary.summary_text ?? t("memory.noSummary")}</p>
              <div className="memory-meta">
                <span>{t("memory.entryCount", { count: summary.entry_count })}</span>
                {summary.summary_digest && (
                  <span>{t("memory.summaryDigest", { digest: summary.summary_digest })}</span>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state-v2 memory-empty">
              <Lightbulb size={48} />
              <p>{t("memory.emptySummary")}</p>
              <span>{t("memory.emptySummaryHint")}</span>
            </div>
          )}
        </div>

        <div className="section-card-v2">
          <div className="section-header-v2">
            <h3 className="section-title-v2">
              <Search size={20} />
              Memory Retrieval Diagnostics
            </h3>
          </div>
          <div className="memory-actions">
            <input
              className="form-select"
              aria-label="Memory retrieval query"
              placeholder="Search ranking signals"
              value={retrievalQuery}
              onChange={(event) => setRetrievalQuery(event.target.value)}
            />
            <button
              type="button"
              className="action-btn primary"
              onClick={handleRetrieve}
              disabled={retrievalState !== "idle" || !retrievalQuery.trim()}
              aria-busy={retrievalState === "searching"}
            >
              <Search size={16} />
              {retrievalState === "searching" ? "Inspecting..." : "Inspect Retrieval"}
            </button>
          </div>
          {retrievalHits.length ? (
            <div className="memory-list">
              {retrievalHits.map((hit) => (
                <div key={hit.memory_id} className="memory-item">
                  <div className="memory-item-header">
                    <span className="memory-id">{hit.memory_id}</span>
                    <span className="memory-status active">score {hit.score.toFixed(2)}</span>
                  </div>
                  <p className="memory-text">{hit.summary_text}</p>
                  <div className="memory-meta">
                    <span>Matched terms: {hit.matched_terms.join(", ") || "none"}</span>
                    <span>Reasons: {hit.match_reasons.join(", ") || "none"}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="memory-content">
              <p className="memory-summary">
                Run a retrieval query to inspect matched terms and ranking reasons.
              </p>
            </div>
          )}
        </div>

        {memories.length > 0 && (
          <div className="section-card-v2">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <Brain size={20} />
                {t("memory.longTermMemory")}
              </h3>
            </div>
            <div className="memory-list">
              {memories.map((memory) => (
                <div key={memory.memory_id} className="memory-item">
                  <div className="memory-item-header">
                    <span className="memory-id">{memory.memory_id}</span>
                    <span className={`memory-status ${memory.status.toLowerCase()}`}>
                      {getStatusLabel(memory.status, locale)}
                    </span>
                  </div>
                  <p className="memory-text">{memory.summary_text}</p>
                  {memory.status.toLowerCase() === "active" && (
                    <button
                      type="button"
                      className="memory-disable-btn"
                      onClick={() => handleDisable(memory.memory_id)}
                      disabled={actionState !== "idle"}
                      aria-busy={actionState === "disabling"}
                    >
                      {actionState === "disabling" ? t("memory.disabling") : t("memory.disable")}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 🔐 认证弹窗 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
