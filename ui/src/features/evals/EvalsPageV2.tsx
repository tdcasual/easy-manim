import { useEffect, useState, useCallback } from "react";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import { Link } from "react-router-dom";
import {
  BarChart3,
  RefreshCw,
  Loader2,
  ArrowRight,
  CheckCircle2,
  XCircle,
  ClipboardList,
  AlertCircle,
} from "lucide-react";
import { useSession } from "../auth/useSession";
import {
  EvalRunSummary,
  listEvals,
  listStrategyDecisions,
  readEvalDeliveryRate,
  readEvalQualityPassRate,
  StrategyDecisionTimelineItem,
} from "../../lib/evalsApi";
import { useI18n } from "../../app/locale";
import { SkeletonMetricCard, SkeletonCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/useARIAMessage";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

const qualityRateIconColors = {
  strong: "#22c55e",
  medium: "#f59e0b",
  weak: "#ef4444",
} as const;

export function EvalsPageV2() {
  const { sessionToken } = useSession();
  const { t } = useI18n();
  const { showAuthModal, closeAuthModal } = useAuthGuard();
  const [items, setItems] = useState<EvalRunSummary[]>([]);
  const [decisions, setDecisions] = useState<StrategyDecisionTimelineItem[]>([]);
  const { status, error, startLoading, setErrorState, succeed } = useAsyncStatus();
  const { ARIALiveRegion, announcePolite } = useARIAMessage();

  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    startLoading();
    try {
      const [evalResponse, decisionResponse] = await Promise.all([
        listEvals(sessionToken),
        listStrategyDecisions(sessionToken),
      ]);
      setItems(Array.isArray(evalResponse.items) ? evalResponse.items : []);
      setDecisions(Array.isArray(decisionResponse.items) ? decisionResponse.items : []);
      succeed();
      announcePolite(t("evals.loaded", { count: evalResponse.items?.length || 0 }));
    } catch {
      setErrorState(t("evals.loadFailed"));
      announcePolite(t("evals.loadFailedShort"));
    }
  }, [sessionToken, announcePolite, t, startLoading, succeed, setErrorState]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const qualityRates = items
    .map((item) => readEvalQualityPassRate(item.report))
    .filter((v): v is number => v !== null);
  const deliveryRates = items
    .map((item) => readEvalDeliveryRate(item.report))
    .filter((v): v is number => v !== null);
  const averageQualityPassRate = qualityRates.length
    ? qualityRates.reduce((a, b) => a + b, 0) / qualityRates.length
    : null;
  const averageDeliveryRate = deliveryRates.length
    ? deliveryRates.reduce((a, b) => a + b, 0) / deliveryRates.length
    : null;

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

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-pink-500">
            {t("evals.page.eyebrow")}
          </div>
          <h1 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100 sm:text-3xl">
            {t("evals.page.title")}
          </h1>
          <p className="text-sm text-cloud-500 dark:text-cloud-400">
            {t("evals.page.description")}
          </p>
        </div>
        <button
          className="flex items-center gap-2 rounded-xl border border-white/60 bg-white/60 px-4 py-2 text-sm font-semibold text-cloud-700 shadow-sm backdrop-blur-sm transition-all hover:-translate-y-0.5 hover:bg-white hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 dark:border-white/10 dark:bg-slate-900/60 dark:text-cloud-200"
          onClick={refresh}
          disabled={status === "loading"}
        >
          {status === "loading" ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <RefreshCw size={18} />
          )}
          {t("evals.refresh")}
        </button>
      </div>

      {error && (
        <div
          className="mb-5 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-900/30 dark:bg-red-900/20 dark:text-red-400"
          role="alert"
        >
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {status === "loading" && items.length === 0 ? (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex items-center gap-4 rounded-2xl border border-lavender-200 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-lavender-100 text-lavender-600 dark:bg-lavender-900/30 dark:text-lavender-300">
              <BarChart3 size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
                {t("evals.runCount")}
              </p>
              <h3 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {items.length}
              </h3>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-2xl border border-mint-200 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-mint-100 text-mint-600 dark:bg-mint-900/30 dark:text-mint-300">
              <CheckCircle2 size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
                {t("evals.averagePassRate")}
              </p>
              <h3 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {formatPercent(averageQualityPassRate)}
              </h3>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-2xl border border-sky-200 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-100 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300">
              <BarChart3 size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
                {t("evals.averageDeliveryRate")}
              </p>
              <h3 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {formatPercent(averageDeliveryRate)}
              </h3>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-2xl border border-sky-200 bg-white/60 p-4 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-100 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300">
              <ClipboardList size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
                {t("evals.visibleCases")}
              </p>
              <h3 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {items.reduce((sum, item) => sum + item.total_cases, 0)}
              </h3>
            </div>
          </div>
        </div>
      )}

      <div className="mb-5 rounded-2xl border border-white/60 bg-white/60 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
        <div className="border-b border-white/60 px-5 py-4 dark:border-white/10">
          <h3 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
            <BarChart3 size={20} />
            {t("evals.recentRuns")}
          </h3>
        </div>

        <div className="flex flex-col p-2">
          {status === "loading" && items.length === 0 ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : items.length > 0 ? (
            items.map((run, index) => {
              const qualityRate = readEvalQualityPassRate(run.report);
              const deliveryRate = readEvalDeliveryRate(run.report);
              return (
                <Link
                  key={run.run_id}
                  to={`/evals/${encodeURIComponent(run.run_id)}`}
                  className="group flex animate-slide-up items-center gap-4 rounded-xl px-4 py-4 text-inherit no-underline transition-colors hover:bg-white/60 dark:hover:bg-slate-800/60"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-cloud-800 dark:text-cloud-100">
                      {run.run_id}
                    </div>
                    <div className="text-xs text-cloud-500 dark:text-cloud-400">
                      {run.suite_id} · {run.provider}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <div className="flex items-center gap-1 text-sm font-semibold text-cloud-800 dark:text-cloud-100">
                      {qualityRate !== null ? (
                        <>
                          {qualityRate >= 0.8 ? (
                            <CheckCircle2 size={16} color={qualityRateIconColors.strong} />
                          ) : qualityRate >= 0.5 ? (
                            <BarChart3 size={16} color={qualityRateIconColors.medium} />
                          ) : (
                            <XCircle size={16} color={qualityRateIconColors.weak} />
                          )}
                          {formatPercent(qualityRate)}
                        </>
                      ) : (
                        "—"
                      )}
                    </div>
                    <div className="text-xs text-cloud-500 dark:text-cloud-400">
                      {deliveryRate !== null
                        ? `${t("evals.deliveryRateInline", { rate: formatPercent(deliveryRate) })} · ${t("evals.casesCount", { count: run.total_cases })}`
                        : t("evals.casesCount", { count: run.total_cases })}
                    </div>
                  </div>
                  <ArrowRight
                    size={16}
                    className="shrink-0 text-cloud-400 opacity-0 transition-all group-hover:translate-x-1 group-hover:opacity-100 group-hover:text-pink-500"
                  />
                </Link>
              );
            })
          ) : error && items.length === 0 ? (
            <div className="flex flex-col items-center px-6 py-10 text-center text-cloud-500">
              <AlertCircle size={48} className="mb-3 text-cloud-400" />
              <p className="text-base font-semibold text-cloud-700 dark:text-cloud-200">
                {t("evals.loadFailedShort")}
              </p>
              <span className="text-sm">{t("evals.loadFailedHint")}</span>
            </div>
          ) : (
            <div className="flex flex-col items-center px-6 py-10 text-center text-cloud-500">
              <ClipboardList size={48} className="mb-3 text-cloud-400" />
              <p className="text-base font-semibold text-cloud-700 dark:text-cloud-200">
                {t("evals.empty")}
              </p>
              <span className="text-sm">{t("evals.emptyHint")}</span>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-white/60 bg-white/60 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-slate-900/60">
        <div className="border-b border-white/60 px-5 py-4 dark:border-white/10">
          <h3 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
            <ClipboardList size={20} />
            Recent Shadow Decisions
          </h3>
        </div>

        <div className="flex flex-col p-2">
          {decisions.length > 0 ? (
            decisions.slice(0, 5).map((decision, index) => (
              <div
                key={`${decision.strategy_id}:${decision.recorded_at}`}
                className="flex animate-slide-up items-center gap-4 rounded-xl px-4 py-4"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-cloud-800 dark:text-cloud-100">
                    {decision.strategy_id}
                  </div>
                  <div className="text-xs text-cloud-500 dark:text-cloud-400">
                    {decision.kind} · {decision.promotion_decision.mode ?? "shadow"}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="text-sm font-semibold text-cloud-800 dark:text-cloud-100">
                    {decision.promotion_decision.approved ? "approved" : "not approved"}
                  </div>
                  <div className="text-xs text-cloud-500 dark:text-cloud-400">
                    {decision.promotion_decision.reasons.join(", ") || "no blockers"}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center px-6 py-10 text-center text-cloud-500">
              <ClipboardList size={48} className="mb-3 text-cloud-400" />
              <p className="text-base font-semibold text-cloud-700 dark:text-cloud-200">
                No shadow decisions yet.
              </p>
              <span className="text-sm">
                Run a strategy challenger evaluation to populate the decision timeline.
              </span>
            </div>
          )}
        </div>
      </div>

      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
