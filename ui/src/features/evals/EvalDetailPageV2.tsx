import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, BarChart3, Clock, AlertCircle, ClipboardList } from "lucide-react";
import { useSession } from "../auth/useSession";
import {
  EvalRunSummary,
  getEval,
  listStrategyDecisions,
  readEvalDeliveryRate,
  readEvalQualityPassRate,
  StrategyDecisionTimelineItem,
} from "../../lib/evalsApi";
import { useI18n } from "../../app/locale";
import { SkeletonCard } from "../../components/Skeleton";
import { getStatusLabel } from "../../app/ui";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import { cn } from "../../lib/utils";

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function getRateTone(value: number | null): string {
  if (value === null) return "";
  if (value >= 0.8) return "success";
  if (value >= 0.5) return "warning";
  return "error";
}

export function EvalDetailPageV2() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const { sessionToken } = useSession();
  const { locale, t } = useI18n();
  const { showAuthModal, closeAuthModal } = useAuthGuard();
  const [run, setRun] = useState<EvalRunSummary | null>(null);
  const [decisions, setDecisions] = useState<StrategyDecisionTimelineItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || !sessionToken) return;
    Promise.all([getEval(runId, sessionToken), listStrategyDecisions(sessionToken)])
      .then(([nextRun, nextDecisions]) => {
        setRun(nextRun);
        setDecisions(Array.isArray(nextDecisions.items) ? nextDecisions.items : []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : t("common.loadingFailed")));
  }, [runId, sessionToken, t]);

  if (!runId) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="rounded-2xl border border-cloud-200 bg-white px-6 py-10 text-center shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <p className="text-lg font-semibold text-cloud-700 dark:text-cloud-200">
            {t("evalDetail.missingRunId")}
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="rounded-2xl border border-cloud-200 bg-white px-6 py-10 text-center shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <p className="text-lg font-semibold text-cloud-700 dark:text-cloud-200">
            {t("evalDetail.loadFailed", { error })}
          </p>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-5 rounded-2xl border border-cloud-200 bg-white p-4 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <SkeletonCard />
        </div>
        <div className="mb-5 rounded-2xl border border-cloud-200 bg-white p-4 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <SkeletonCard />
        </div>
        <div className="rounded-2xl border border-cloud-200 bg-white p-4 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <SkeletonCard />
        </div>
      </div>
    );
  }

  const cases = Array.isArray(run.items) ? run.items : [];
  const qualityPassRate = readEvalQualityPassRate(run.report);
  const deliveryRate = readEvalDeliveryRate(run.report);
  const matchingDecisions = decisions.filter(
    (item) => item.challenger_run_id === run.run_id || item.baseline_run_id === run.run_id
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:py-8">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="mb-2 flex items-center gap-1 text-sm text-cloud-500 hover:text-pink-500 dark:text-cloud-400"
          >
            <ArrowLeft size={18} />
            {t("evalDetail.back")}
          </button>
          <h1 className="text-2xl font-bold text-cloud-800 dark:text-cloud-100 sm:text-3xl">
            {t("evalDetail.title")}
          </h1>
          <p className="text-sm font-mono text-cloud-500 dark:text-cloud-400">{run.run_id}</p>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-1 rounded-2xl border border-cloud-200 bg-white p-5 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <span className="text-xs uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
            {t("evalDetail.suite")}
          </span>
          <span className="text-xl font-bold text-cloud-800 dark:text-cloud-100">
            {run.suite_id}
          </span>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl border border-cloud-200 bg-white p-5 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <span className="text-xs uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
            {t("evalDetail.cases")}
          </span>
          <span className="text-xl font-bold text-cloud-800 dark:text-cloud-100">
            {run.total_cases}
          </span>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl border border-cloud-200 bg-white p-5 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <span className="text-xs uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
            {t("evalDetail.passRate")}
          </span>
          <span
            className={cn(
              "text-xl font-bold",
              getRateTone(qualityPassRate) === "success" && "text-mint-600 dark:text-mint-300",
              getRateTone(qualityPassRate) === "warning" && "text-amber-600 dark:text-amber-300",
              getRateTone(qualityPassRate) === "error" && "text-red-600 dark:text-red-300",
              getRateTone(qualityPassRate) === "" && "text-cloud-800 dark:text-cloud-100"
            )}
          >
            {formatPercent(qualityPassRate)}
          </span>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl border border-cloud-200 bg-white p-5 shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
          <span className="text-xs uppercase tracking-wide text-cloud-500 dark:text-cloud-400">
            {t("evalDetail.deliveryRate")}
          </span>
          <span
            className={cn(
              "text-xl font-bold",
              getRateTone(deliveryRate) === "success" && "text-mint-600 dark:text-mint-300",
              getRateTone(deliveryRate) === "warning" && "text-amber-600 dark:text-amber-300",
              getRateTone(deliveryRate) === "error" && "text-red-600 dark:text-red-300",
              getRateTone(deliveryRate) === "" && "text-cloud-800 dark:text-cloud-100"
            )}
          >
            {formatPercent(deliveryRate)}
          </span>
        </div>
      </div>

      <div className="mb-5 rounded-2xl border border-cloud-200 bg-white shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
        <div className="border-b border-cloud-200 px-5 py-4 dark:border-cloud-800">
          <h2 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
            <BarChart3 size={20} />
            {t("evalDetail.caseResults")}
          </h2>
        </div>

        <div className="flex flex-col p-2">
          {cases.length > 0 ? (
            cases.map((item) => {
              const normalizedStatus = item.status.toLowerCase();
              const deliveryPassed = item.delivery_passed ?? normalizedStatus === "completed";
              const qualityPassed = item.quality_passed ?? normalizedStatus === "completed";
              const quality =
                typeof item.quality_score === "number" ? item.quality_score.toFixed(2) : "—";
              const duration =
                typeof item.duration_seconds === "number"
                  ? t("evalDetail.durationSeconds", { count: item.duration_seconds.toFixed(1) })
                  : "—";
              const issueCodes =
                Array.isArray(item.issue_codes) && item.issue_codes.length
                  ? item.issue_codes.join(", ")
                  : t("evalDetail.none");

              return (
                <div
                  key={`${item.task_id}:${item.root_task_id}`}
                  className="rounded-xl border-b border-cloud-200 p-4 last:border-b-0 dark:border-cloud-800"
                >
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-sm font-medium text-cloud-800 dark:text-cloud-100">
                      {item.task_id}
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {item.manual_review_required && (
                        <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                          <AlertCircle size={12} />
                          {t("evalDetail.review")}
                        </span>
                      )}
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                          normalizedStatus === "completed"
                            ? "bg-mint-100 text-mint-700 dark:bg-mint-900/30 dark:text-mint-300"
                            : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                        )}
                      >
                        {getStatusLabel(item.status, locale)}
                      </span>
                      {qualityPassed ? (
                        <span className="rounded-full bg-mint-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-mint-700 dark:bg-mint-900/30 dark:text-mint-300">
                          {t("evalDetail.qualityPassed")}
                        </span>
                      ) : deliveryPassed ? (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                          {t("evalDetail.deliveryOnly")}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-4 text-xs text-cloud-500 dark:text-cloud-400">
                    <div className="flex items-center gap-1">
                      <Clock size={14} />
                      {duration}
                    </div>
                    <div>{t("evalDetail.qualityScore", { value: quality })}</div>
                    <div className="text-cloud-600 dark:text-cloud-300">
                      {t("evalDetail.issues", { value: issueCodes })}
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center px-6 py-10 text-center text-cloud-500">
              <ClipboardList size={48} className="mb-3 text-cloud-400" />
              <p className="text-base font-semibold text-cloud-700 dark:text-cloud-200">
                {t("evalDetail.noCases")}
              </p>
              <span className="text-sm">{t("evalDetail.noCasesHint")}</span>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-cloud-200 bg-white shadow-sm dark:border-cloud-800 dark:bg-cloud-900">
        <div className="border-b border-cloud-200 px-5 py-4 dark:border-cloud-800">
          <h2 className="flex items-center gap-2 text-base font-bold text-cloud-800 dark:text-cloud-100">
            <ClipboardList size={20} />
            Decision Timeline
          </h2>
        </div>

        <div className="flex flex-col p-2">
          {matchingDecisions.length > 0 ? (
            matchingDecisions.map((item) => (
              <div
                key={`${item.strategy_id}:${item.recorded_at}`}
                className="rounded-xl border-b border-cloud-200 p-4 last:border-b-0 dark:border-cloud-800"
              >
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-sm font-medium text-cloud-800 dark:text-cloud-100">
                    {item.strategy_id}
                  </span>
                  <div className="flex gap-2">
                    <span className="rounded-full bg-cloud-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-cloud-700 dark:bg-cloud-800 dark:text-cloud-300">
                      {item.promotion_decision.mode ?? "shadow"}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        item.promotion_decision.approved
                          ? "bg-mint-100 text-mint-700 dark:bg-mint-900/30 dark:text-mint-300"
                          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                      )}
                    >
                      {item.promotion_decision.approved ? "approved" : "not approved"}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-4 text-xs text-cloud-500 dark:text-cloud-400">
                  <div>{item.kind}</div>
                  <div>Reasons: {item.promotion_decision.reasons.join(", ") || "no blockers"}</div>
                  <div>Recorded at: {item.recorded_at}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center px-6 py-10 text-center text-cloud-500">
              <ClipboardList size={48} className="mb-3 text-cloud-400" />
              <p className="text-base font-semibold text-cloud-700 dark:text-cloud-200">
                No matching strategy decisions.
              </p>
              <span className="text-sm">
                Shadow challenger runs linked to this eval will appear here.
              </span>
            </div>
          )}
        </div>
      </div>

      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
