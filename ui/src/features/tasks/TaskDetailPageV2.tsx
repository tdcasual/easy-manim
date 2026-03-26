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
  TaskResult 
} from "../../lib/tasksApi";
import { resolveApiUrl } from "../../lib/api";
import { SkeletonCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/ARIALiveRegion";
import { useConfirm } from "../../components/ConfirmDialog";
import { getStatusLabel } from "../../app/ui";
import "./TaskDetailPageV2.css";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function TaskDetailPageV2() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { sessionToken } = useSession();
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
        
        if (!TERMINAL.has(String(nextSnapshot.status))) {
          const delay = Math.min(250 * 2 ** attempt, 5000);
          attempt += 1;
          timer = window.setTimeout(loadOnce, delay);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "加载失败");
      }
    }
    
    loadOnce();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [taskId, sessionToken, reloadTick]);
  
  async function onRevise() {
    if (!taskId || !sessionToken) return;
    const trimmed = feedback.trim();
    if (!trimmed) return;
    
    setError(null);
    setActionState("revise");
    try {
      await reviseTask(taskId, trimmed, sessionToken);
      setFeedback("");
      setReloadTick(t => t + 1);
      announcePolite("修订请求已提交");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "修订失败";
      setError(errorMsg);
      announcePolite(`修订失败: ${errorMsg}`);
    } finally {
      setActionState("idle");
    }
  }
  
  async function onRetry() {
    if (!taskId || !sessionToken) return;
    
    const confirmed = await confirm({
      title: "重试任务",
      message: "重新执行任务将丢弃之前的进度，是否继续？",
      confirmText: "确认重试",
      cancelText: "取消",
      danger: false,
    });
    
    if (!confirmed) return;
    
    setError(null);
    setActionState("retry");
    try {
      await retryTask(taskId, sessionToken);
      setReloadTick(t => t + 1);
      announcePolite("任务已重试");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "重试失败";
      setError(errorMsg);
      announcePolite(`重试失败: ${errorMsg}`);
    } finally {
      setActionState("idle");
    }
  }
  
  async function onCancel() {
    if (!taskId || !sessionToken) return;
    
    const confirmed = await confirm({
      title: "取消任务",
      message: "取消后任务将停止执行，不可恢复。是否继续？",
      confirmText: "确认取消",
      cancelText: "继续执行",
      danger: true,
    });
    
    if (!confirmed) return;
    
    setError(null);
    setActionState("cancel");
    try {
      await cancelTask(taskId, sessionToken);
      setReloadTick(t => t + 1);
      announcePolite("任务已取消");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "取消失败";
      setError(errorMsg);
      announcePolite(`取消失败: ${errorMsg}`);
    } finally {
      setActionState("idle");
    }
  }
  
  if (!taskId) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">缺少任务 ID</div>
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
              返回
            </button>
            <h1 className="page-title-v2">任务详情</h1>
            <p className="page-description-v2">{taskId}</p>
          </div>
        </div>
        <div className="task-detail-error" role="alert">
          加载失败: {error}
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
  const terminal = TERMINAL.has(status);
  const videoUrl = resolveApiUrl(result?.video_download_url);
  const displayTitle = snapshot.display_title || taskId;
  
  const statusConfig: Record<string, { icon: React.ElementType; colorVar: string; label: string }> = {
    completed: { icon: CheckCircle2, colorVar: 'var(--success)', label: getStatusLabel("completed") },
    rendering: { icon: Loader2, colorVar: 'var(--accent-blue)', label: getStatusLabel("rendering") },
    running: { icon: Clock, colorVar: 'var(--accent-cyan)', label: getStatusLabel("running") },
    queued: { icon: Clock, colorVar: 'var(--warning)', label: getStatusLabel("queued") },
    failed: { icon: XCircle, colorVar: 'var(--error)', label: getStatusLabel("failed") },
    cancelled: { icon: XCircle, colorVar: 'var(--text-muted)', label: getStatusLabel("cancelled") },
  };
  
  const currentStatus = statusConfig[status.toLowerCase()] || { 
    icon: Clock, 
    colorVar: 'var(--text-muted)', 
    label: getStatusLabel(status) 
  };
  const StatusIcon = currentStatus.icon;
  const phaseLabel = getStatusLabel(String(snapshot.phase));
  
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
            返回
          </button>
          <h1 className="page-title-v2">{displayTitle}</h1>
          <p className="page-description-v2">{taskId}</p>
        </div>
        <button 
          className="refresh-btn"
          onClick={() => setReloadTick(t => t + 1)}
        >
          <RefreshCw size={18} />
          刷新
        </button>
      </div>

      {error && (
        <div className="task-detail-error" role="alert">
          操作失败: {error}
        </div>
      )}
      
      {/* 状态栏 */}
      <div className="task-status-bar" style={{ '--status-color': currentStatus.colorVar } as React.CSSProperties}>
        <div className="status-icon-wrapper" style={{ background: `${currentStatus.colorVar}20` }}>
          <StatusIcon size={24} style={{ color: currentStatus.colorVar }} className={status === 'running' ? 'spin' : ''} />
        </div>
        <div className="status-info">
          <span className="status-label">{currentStatus.label}</span>
          <span className="status-phase">{phaseLabel}</span>
        </div>
        <div className="status-attempts">
          尝试次数: {snapshot.attempt_count || 0}
        </div>
      </div>
      
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
                poster={result?.preview_download_urls?.[0]}
              />
            </div>
          )}
          
          {/* 操作面板 */}
          <div className="section-card-v2">
            <h3 className="section-title-v2">操作</h3>
            
            <div className="action-group">
              <label className="form-label-v2">修订说明</label>
              <textarea
                className="form-textarea-v2"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="描述需要修改的内容..."
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
                  <><Loader2 size={18} className="spin" /> 提交中...</>
                ) : (
                  <><RotateCcw size={18} /> 提交修订</>
                )}
              </button>
            </div>
            
            <div className="quick-actions">
              {status.toLowerCase() === "failed" && (
                <button
                  type="button"
                  className="action-btn secondary"
                  onClick={onRetry}
                  disabled={actionState !== "idle"}
                  aria-busy={actionState === "retry"}
                >
                  <RotateCcw size={16} />
                  {actionState === "retry" ? "重试中..." : "重试"}
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
                  {actionState === "cancel" ? "取消中..." : "取消任务"}
                </button>
              )}
            </div>
          </div>
        </div>
        
        <div className="side-column">
          {/* 结果信息 */}
          <div className="section-card-v2">
            <h3 className="section-title-v2">结果</h3>
            <div className="info-list">
              <div className="info-item">
                <span className="info-label">状态</span>
                <span className="info-value" style={{ color: currentStatus.colorVar }}>
                  {currentStatus.label}
                </span>
              </div>
              <div className="info-item">
                <span className="info-label">阶段</span>
                <span className="info-value">{phaseLabel}</span>
              </div>
              <div className="info-item">
                <span className="info-label">尝试次数</span>
                <span className="info-value">{snapshot.attempt_count || 0}</span>
              </div>
              {result?.summary && (
                <div className="info-item full-width">
                  <span className="info-label">摘要</span>
                  <p className="info-summary">{result.summary}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
