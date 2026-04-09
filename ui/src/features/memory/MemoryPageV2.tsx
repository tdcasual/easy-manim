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
import { cn } from "../../lib/utils";

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
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="flex flex-col items-center justify-center rounded-2xl border border-white/60 bg-white/60 px-6 py-16 text-center shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
          <p className="text-lg font-semibold text-cloud-700 dark:text-cloud-200">
            {t("common.notLoggedIn")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:py-8">
      <ARIALiveRegion />
      <ConfirmDialog />

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-pink-500">
            {t("memory.page.eyebrow")}
          </div>
          <h1 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100 sm:text-3xl">
            {t("memory.page.title")}
          </h1>
          <p className="text-sm text-cloud-500 dark:text-cloud-400">
            {t("memory.page.description")}
          </p>
        </div>
        <button
          className="flex items-center gap-2 rounded-xl border border-white/60 bg-white/60 px-4 py-2 text-sm font-semibold text-cloud-700 shadow-sm backdrop-blur-sm transition-all hover:-translate-y-0.5 hover:bg-white hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-slate-900/60 dark:text-cloud-200"
          onClick={refresh}
          disabled={status === "loading"}
          aria-busy={status === "loading"}
        >
          {status === "loading" ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <RefreshCw size={18} />
          )}
          {t("memory.refresh")}
        </button>
      </div>

      {error && (
        <div className="mb-5 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-900/30 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {actionError && (
        <div className="mb-5 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-900/30 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={16} />
          {actionError}
        </div>
      )}

      {status === "loading" && !summary ? (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex items-center gap-4 rounded-2xl border border-pink-200 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-pink-100 text-pink-600 dark:bg-pink-900/30 dark:text-pink-300">
              <Brain size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
                {t("memory.sessionEntries")}
              </p>
              <h3 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {summary?.entry_count ?? 0}
              </h3>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-2xl border border-mint-200 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-mint-100 text-mint-600 dark:bg-mint-900/30 dark:text-mint-300">
              <Brain size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
                {t("memory.activeMemories")}
              </p>
              <h3 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {activeCount}
              </h3>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-5">
        <div className="rounded-2xl border border-white/60 bg-white/60 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/60 px-5 py-4 dark:border-white/10">
            <h3 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
              <Brain size={20} />
              {t("memory.sessionMemory")}
            </h3>
            <div className="flex gap-2">
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-lg bg-red-50 px-3 py-2 text-xs font-semibold text-red-600 transition-colors hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
                onClick={handleClear}
                disabled={actionState !== "idle"}
                aria-busy={actionState === "clearing"}
              >
                <Trash2 size={16} />
                {actionState === "clearing" ? t("memory.clearing") : t("memory.clear")}
              </button>
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-lg bg-mint-50 px-3 py-2 text-xs font-semibold text-mint-600 transition-colors hover:bg-mint-100 dark:bg-mint-900/20 dark:text-mint-400"
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
            <div className="flex flex-col items-center gap-3 px-5 py-10 text-cloud-500">
              <Loader2 size={24} className="animate-spin" />
              <p>{t("memory.loading")}</p>
            </div>
          ) : summary ? (
            <div className="p-5">
              <p className="mb-4 break-words text-sm leading-relaxed text-cloud-700 dark:text-cloud-200">
                {summary.summary_text ?? t("memory.noSummary")}
              </p>
              <div className="flex flex-wrap gap-4 text-xs text-cloud-500 dark:text-cloud-400">
                <span>{t("memory.entryCount", { count: summary.entry_count })}</span>
                {summary.summary_digest && (
                  <span>{t("memory.summaryDigest", { digest: summary.summary_digest })}</span>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center px-5 py-10 text-center text-cloud-500">
              <Lightbulb size={48} className="mb-3 text-cloud-400" />
              <p className="text-base font-semibold text-cloud-700 dark:text-cloud-200">
                {t("memory.emptySummary")}
              </p>
              <span className="text-sm">{t("memory.emptySummaryHint")}</span>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-white/60 bg-white/60 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
          <div className="border-b border-white/60 px-5 py-4 dark:border-white/10">
            <h3 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
              <Search size={20} />
              Memory Retrieval Diagnostics
            </h3>
          </div>
          <div className="p-5">
            <div className="flex flex-wrap gap-2">
              <input
                className="min-w-[200px] flex-1 rounded-xl border-2 border-transparent bg-cloud-100 px-4 py-2 text-sm text-cloud-800 outline-none transition-all focus:border-pink-300 focus:bg-white dark:bg-slate-800 dark:text-cloud-100"
                aria-label="Memory retrieval query"
                placeholder="Search ranking signals"
                value={retrievalQuery}
                onChange={(event) => setRetrievalQuery(event.target.value)}
              />
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-pink-400 to-peach-400 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                onClick={handleRetrieve}
                disabled={retrievalState !== "idle" || !retrievalQuery.trim()}
                aria-busy={retrievalState === "searching"}
              >
                <Search size={16} />
                {retrievalState === "searching" ? "Inspecting..." : "Inspect Retrieval"}
              </button>
            </div>
            {retrievalHits.length ? (
              <div className="mt-4 flex flex-col gap-3">
                {retrievalHits.map((hit) => (
                  <div
                    key={hit.memory_id}
                    className="rounded-xl border border-white/60 bg-white/40 p-4 dark:border-white/10 dark:bg-slate-800/40"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-xs text-cloud-500 dark:text-cloud-400">
                        {hit.memory_id}
                      </span>
                      <span className="rounded-full bg-mint-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-mint-700 dark:bg-mint-900/30 dark:text-mint-300">
                        score {hit.score.toFixed(2)}
                      </span>
                    </div>
                    <p className="mb-2 break-words text-sm text-cloud-700 dark:text-cloud-200">
                      {hit.summary_text}
                    </p>
                    <div className="flex flex-wrap gap-3 break-words text-xs text-cloud-500 dark:text-cloud-400">
                      <span>{t("memory.matchedTermsLabel")}: {hit.matched_terms.join(", ") || t("profile.none")}</span>
                      <span>{t("memory.matchReasonsLabel")}: {hit.match_reasons.join(", ") || t("profile.none")}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4">
                <p className="text-sm text-cloud-600 dark:text-cloud-300">
                  Run a retrieval query to inspect matched terms and ranking reasons.
                </p>
              </div>
            )}
          </div>
        </div>

        {memories.length > 0 && (
          <div className="rounded-2xl border border-white/60 bg-white/60 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="border-b border-white/60 px-5 py-4 dark:border-white/10">
              <h3 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
                <Brain size={20} />
                {t("memory.longTermMemory")}
              </h3>
            </div>
            <div className="flex flex-col">
              {memories.map((memory) => (
                <div
                  key={memory.memory_id}
                  className="border-b border-white/60 p-4 last:border-b-0 dark:border-white/10"
                >
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs text-cloud-500 dark:text-cloud-400">
                      {memory.memory_id}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        memory.status.toLowerCase() === "active"
                          ? "bg-mint-100 text-mint-700 dark:bg-mint-900/30 dark:text-mint-300"
                          : "bg-cloud-100 text-cloud-600 dark:bg-slate-700 dark:text-cloud-300"
                      )}
                    >
                      {getStatusLabel(memory.status, locale)}
                    </span>
                  </div>
                  <p className="mb-3 text-sm text-cloud-700 dark:text-cloud-200">
                    {memory.summary_text}
                  </p>
                  {memory.status.toLowerCase() === "active" && (
                    <button
                      type="button"
                      className="rounded-md bg-red-50 px-3 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
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

      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
