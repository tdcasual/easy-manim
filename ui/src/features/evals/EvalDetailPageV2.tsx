import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, BarChart3, Clock, AlertCircle, ClipboardList } from "lucide-react";
import { useSession } from "../auth/useSession";
import { EvalRunSummary, getEval } from "../../lib/evalsApi";
import { useI18n } from "../../app/locale";
import { SkeletonCard } from "../../components/Skeleton";
import { getStatusLabel } from "../../app/ui";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import "./EvalDetailPageV2.css";

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function readSuccessRate(report?: Record<string, unknown>): number | null {
  const raw = report?.success_rate;
  return typeof raw === "number" && Number.isFinite(raw) ? raw : null;
}

export function EvalDetailPageV2() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const { sessionToken } = useSession();
  const { locale, t } = useI18n();
  const { showAuthModal, closeAuthModal } = useAuthGuard();
  const [run, setRun] = useState<EvalRunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || !sessionToken) return;
    getEval(runId, sessionToken)
      .then(setRun)
      .catch((err) => setError(err instanceof Error ? err.message : t("common.loadingFailed")));
  }, [runId, sessionToken, t]);

  if (!runId) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">{t("evalDetail.missingRunId")}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">{t("evalDetail.loadFailed", { error })}</div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="page-v2">
        <div className="page-header-v2">
          <SkeletonCard />
        </div>
        <div className="eval-detail-header">
          <SkeletonCard />
        </div>
        <div className="section-card-v2">
          <SkeletonCard />
        </div>
      </div>
    );
  }

  const cases = Array.isArray(run.items) ? run.items : [];
  const successRate = readSuccessRate(run.report);

  return (
    <div className="page-v2">
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <button onClick={() => navigate(-1)} className="back-link">
            <ArrowLeft size={18} />
            {t("evalDetail.back")}
          </button>
          <h1 className="page-title-v2">{t("evalDetail.title")}</h1>
          <p className="page-description-v2">{run.run_id}</p>
        </div>
      </div>

      <div className="eval-detail-header">
        <div className="eval-detail-stats">
          <div className="eval-stat">
            <span className="stat-label">{t("evalDetail.suite")}</span>
            <span className="stat-value">{run.suite_id}</span>
          </div>
          <div className="eval-stat">
            <span className="stat-label">{t("evalDetail.cases")}</span>
            <span className="stat-value">{run.total_cases}</span>
          </div>
          <div className="eval-stat">
            <span className="stat-label">{t("evalDetail.passRate")}</span>
            <span
              className={`stat-value ${successRate && successRate >= 0.8 ? "success" : successRate && successRate >= 0.5 ? "warning" : "error"}`}
            >
              {formatPercent(successRate)}
            </span>
          </div>
        </div>
      </div>

      <div className="section-card-v2">
        <div className="section-header-v2">
          <h3 className="section-title-v2">
            <BarChart3 size={20} />
            {t("evalDetail.caseResults")}
          </h3>
        </div>

        <div className="case-list">
          {cases.length > 0 ? (
            cases.map((item) => {
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
                <div key={`${item.task_id}:${item.root_task_id}`} className="case-item">
                  <div className="case-header">
                    <span className="case-id">{item.task_id}</span>
                    <div className="case-badges">
                      {item.manual_review_required && (
                        <span className="case-badge review">
                          <AlertCircle size={12} />
                          {t("evalDetail.review")}
                        </span>
                      )}
                      <span className={`case-badge ${item.status.toLowerCase()}`}>
                        {getStatusLabel(item.status, locale)}
                      </span>
                    </div>
                  </div>
                  <div className="case-details">
                    <div className="case-stat">
                      <Clock size={14} />
                      {duration}
                    </div>
                    <div className="case-stat">
                      {t("evalDetail.qualityScore", { value: quality })}
                    </div>
                    <div className="case-issues">
                      {t("evalDetail.issues", { value: issueCodes })}
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="empty-state-v2 case-empty">
              <ClipboardList size={48} />
              <p>{t("evalDetail.noCases")}</p>
              <span>{t("evalDetail.noCasesHint")}</span>
            </div>
          )}
        </div>
      </div>

      {/* 🔐 认证弹窗 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
