// TaskDetailPage V2 - 占位符实现
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  RefreshCw,
  RotateCcw,
  XCircle,
  CheckCircle2,
  Clock,
  Loader2,
} from "lucide-react";
import { useSession } from "../auth/useSession";
import {
  getTask,
  getTaskResult,
  reviseTask,
  retryTask,
  cancelTask,
  TaskSnapshot,
  TaskResult,
} from "../../lib/tasksApi";
import { resolveApiUrl } from "../../lib/api";
import { useI18n } from "../../app/locale";
import { SkeletonCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/useARIAMessage";
import { useConfirm } from "../../components/useConfirm";
import { getStatusLabel } from "../../app/ui";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import "./TaskDetailPageV2.css";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function TaskDetailPageV2() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { showAuthModal, closeAuthModal } = useAuthGuard();
  const { sessionToken } = useSession();
  const { locale, t } = useI18n();
  const [snapshot, setSnapshot] = useState<TaskSnapshot | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [actionState, setActionState] = useState<"idle" | "revise" | "retry" | "cancel">("idle");
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  const { confirm, ConfirmDialog } = useConfirm();

  useEffect(() => {
    if (!taskId || !sessionToken) return;
    const currentTaskId = taskId;
    const token = sessionToken;
    let cancelled = false;
    let timer: number | null = null;
    let attempt = 0;

    async function loadOnce() {
      try {
        setError(null);
        const nextSnapshot = await getTask(currentTaskId, token);
        if (cancelled) return;
        setSnapshot(nextSnapshot);

        const nextResult = await getTaskResult(currentTaskId, token);
        if (cancelled) return;
        setResult(nextResult);

        const shouldContinuePolling =
          !TERMINAL.has(String(nextSnapshot.status)) || nextSnapshot.delivery_status === "pending";
        if (shouldContinuePolling) {
          const delay = Math.min(250 * 2 ** attempt, 5000);
          attempt += 1;
          timer = window.setTimeout(loadOnce, delay);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : t("common.loadingFailed"));
      }
    }

    loadOnce();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [taskId, sessionToken, reloadTick, t]);

  async function onRevise() {
    if (!taskId || !sessionToken) return;
    const trimmed = feedback.trim();
    if (!trimmed) return;

    setError(null);
    setActionState("revise");
    try {
      await reviseTask(taskId, trimmed, sessionToken);
      setFeedback("");
      setReloadTick((t) => t + 1);
      announcePolite(t("taskDetail.revisionSubmitted"));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("taskDetail.submitRevision");
      setError(errorMsg);
      announcePolite(t("taskDetail.revisionFailed", { error: errorMsg }));
    } finally {
      setActionState("idle");
    }
  }

  async function onRetry() {
    if (!taskId || !sessionToken) return;

    const confirmed = await confirm({
      title: t("taskDetail.retryConfirmTitle"),
      message: t("taskDetail.retryConfirmMessage"),
      confirmText: t("taskDetail.retryConfirmAction"),
      cancelText: t("common.cancel"),
      danger: false,
    });

    if (!confirmed) return;

    setError(null);
    setActionState("retry");
    try {
      await retryTask(taskId, sessionToken);
      setReloadTick((t) => t + 1);
      announcePolite(t("taskDetail.retried"));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("taskDetail.retry");
      setError(errorMsg);
      announcePolite(t("taskDetail.retryFailed", { error: errorMsg }));
    } finally {
      setActionState("idle");
    }
  }

  async function onCancel() {
    if (!taskId || !sessionToken) return;

    const confirmed = await confirm({
      title: t("taskDetail.cancelConfirmTitle"),
      message: t("taskDetail.cancelConfirmMessage"),
      confirmText: t("taskDetail.cancelConfirmAction"),
      cancelText: t("taskDetail.cancelKeepRunning"),
      danger: true,
    });

    if (!confirmed) return;

    setError(null);
    setActionState("cancel");
    try {
      await cancelTask(taskId, sessionToken);
      setReloadTick((t) => t + 1);
      announcePolite(t("taskDetail.cancelled"));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("taskDetail.cancelTask");
      setError(errorMsg);
      announcePolite(t("taskDetail.cancelFailed", { error: errorMsg }));
    } finally {
      setActionState("idle");
    }
  }

  if (!taskId) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">{t("taskDetail.missingTaskId")}</div>
      </div>
    );
  }

  if (error && !snapshot) {
    return (
      <div className="page-v2">
        <ARIALiveRegion />
        <ConfirmDialog />
        <div className="page-header-v2">
          <div className="page-header-content-v2">
            <button onClick={() => navigate(-1)} className="back-link">
              <ArrowLeft size={18} />
              {t("taskDetail.back")}
            </button>
            <h1 className="page-title-v2">{t("taskDetail.title")}</h1>
            <p className="page-description-v2">{taskId}</p>
          </div>
        </div>
        <div className="task-detail-error" role="alert">
          {t("taskDetail.loadFailed", { error })}
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="page-v2">
        <ARIALiveRegion />
        <ConfirmDialog />
        <div className="page-header-v2">
          <SkeletonCard />
        </div>
        <div className="content-grid-v2">
          <div className="main-column">
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="side-column">
            <SkeletonCard />
          </div>
        </div>
      </div>
    );
  }

  const status = String(snapshot.status);
  const deliveryMode = result?.completion_mode ?? snapshot.completion_mode ?? null;
  const deliveryPending = snapshot.delivery_status === "pending";
  const terminal = TERMINAL.has(status) && !deliveryPending;
  const videoUrl = resolveApiUrl(result?.video_download_url);
  const previewPosterUrl = resolveApiUrl(result?.preview_download_urls?.[0]);
  const displayTitle = snapshot.display_title ?? taskId;
  const deliveryBannerText =
    deliveryMode === "degraded"
      ? t("taskDetail.deliveryDegraded")
      : deliveryMode === "emergency_fallback"
        ? t("taskDetail.deliveryEmergency")
        : null;

  const statusConfig: Record<string, { icon: React.ElementType; colorVar: string; label: string }> =
    {
      completed: {
        icon: CheckCircle2,
        colorVar: "var(--success)",
        label: getStatusLabel("completed", locale),
      },
      rendering: {
        icon: Loader2,
        colorVar: "var(--accent-blue)",
        label: getStatusLabel("rendering", locale),
      },
      running: {
        icon: Clock,
        colorVar: "var(--accent-cyan)",
        label: getStatusLabel("running", locale),
      },
      queued: { icon: Clock, colorVar: "var(--warning)", label: getStatusLabel("queued", locale) },
      failed: { icon: XCircle, colorVar: "var(--error)", label: getStatusLabel("failed", locale) },
      cancelled: {
        icon: XCircle,
        colorVar: "var(--text-muted)",
        label: getStatusLabel("cancelled", locale),
      },
    };

  const currentStatus = statusConfig[status.toLowerCase()] || {
    icon: Clock,
    colorVar: "var(--text-muted)",
    label: getStatusLabel(status, locale),
  };
  const StatusIcon = currentStatus.icon;
  const phaseLabel = getStatusLabel(String(snapshot.phase), locale);

  return (
    <div className="page-v2">
      {/* ARIA Live 区域 */}
      <ARIALiveRegion />

      {/* 确认对话框 */}
      <ConfirmDialog />

      {/* 头部 */}
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <button onClick={() => navigate(-1)} className="back-link">
            <ArrowLeft size={18} />
            {t("taskDetail.back")}
          </button>
          <h1 className="page-title-v2">{displayTitle}</h1>
          <p className="page-description-v2">{taskId}</p>
        </div>
        <button className="refresh-btn" onClick={() => setReloadTick((t) => t + 1)}>
          <RefreshCw size={18} />
          {t("taskDetail.refresh")}
        </button>
      </div>

      {error && (
        <div className="task-detail-error" role="alert">
          {t("taskDetail.actionFailed", { error })}
        </div>
      )}

      {/* 状态栏 */}
      <div
        className="task-status-bar"
        style={{ "--status-color": currentStatus.colorVar } as React.CSSProperties}
      >
        <div className="status-icon-wrapper" style={{ background: `${currentStatus.colorVar}20` }}>
          <StatusIcon
            size={24}
            style={{ color: currentStatus.colorVar }}
            className={status === "running" ? "spin" : ""}
          />
        </div>
        <div className="status-info">
          <span className="status-label">{currentStatus.label}</span>
          <span className="status-phase">{phaseLabel}</span>
        </div>
        <div className="status-attempts">
          {t("taskDetail.attemptCount", { count: snapshot.attempt_count ?? 0 })}
        </div>
      </div>
      {deliveryBannerText && (
        <div className="task-detail-error" role="status">
          {t("taskDetail.deliveryGuaranteed")} · {deliveryBannerText}
        </div>
      )}

      {/* 主内容 */}
      <div className="content-grid-v2">
        <div className="main-column">
          {/* 视频播放器 */}
          {videoUrl && (
            <div className="section-card-v2 video-player-card">
              <video
                className="main-video-player"
                src={videoUrl}
                controls
                poster={previewPosterUrl ?? undefined}
              />
            </div>
          )}

          {/* 操作面板 */}
          <div className="section-card-v2">
            <h3 className="section-title-v2">{t("taskDetail.actions")}</h3>

            <div className="action-group">
              <label className="form-label-v2">{t("taskDetail.feedbackLabel")}</label>
              <textarea
                className="form-textarea-v2"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder={t("taskDetail.feedbackPlaceholder")}
                rows={4}
                disabled={actionState !== "idle"}
              />
              <button
                type="button"
                className="submit-btn-v2"
                onClick={onRevise}
                disabled={actionState !== "idle" || !feedback.trim()}
                aria-busy={actionState === "revise"}
              >
                {actionState === "revise" ? (
                  <>
                    <Loader2 size={18} className="spin" /> {t("taskDetail.submitting")}
                  </>
                ) : (
                  <>
                    <RotateCcw size={18} /> {t("taskDetail.submitRevision")}
                  </>
                )}
              </button>
            </div>

            <div className="quick-actions">
              {status.toLowerCase() === "failed" && !deliveryPending && (
                <button
                  type="button"
                  className="action-btn secondary"
                  onClick={onRetry}
                  disabled={actionState !== "idle"}
                  aria-busy={actionState === "retry"}
                >
                  <RotateCcw size={16} />
                  {actionState === "retry" ? t("taskDetail.retrying") : t("taskDetail.retry")}
                </button>
              )}
              {!terminal && (
                <button
                  type="button"
                  className="action-btn danger"
                  onClick={onCancel}
                  disabled={actionState !== "idle"}
                  aria-busy={actionState === "cancel"}
                >
                  <XCircle size={16} />
                  {actionState === "cancel"
                    ? t("taskDetail.cancelling")
                    : t("taskDetail.cancelTask")}
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="side-column">
          {/* 结果信息 */}
          <div className="section-card-v2">
            <h3 className="section-title-v2">{t("taskDetail.results")}</h3>
            <div className="info-list">
              <div className="info-item">
                <span className="info-label">{t("taskDetail.status")}</span>
                <span className="info-value" style={{ color: currentStatus.colorVar }}>
                  {currentStatus.label}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">{t("taskDetail.phase")}</span>
                <span className="info-value">{phaseLabel}</span>
              </div>
              <div className="info-item">
                <span className="info-label">{t("taskDetail.attempts")}</span>
                <span className="info-value">{snapshot.attempt_count ?? 0}</span>
              </div>
              {result?.summary && (
                <div className="info-item full-width">
                  <span className="info-label">{t("taskDetail.summary")}</span>
                  <p className="info-summary">{result.summary}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 🔐 认证弹窗 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
