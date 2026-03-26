import { useEffect, useState, useCallback } from "react";
import { Brain, RefreshCw, Trash2, ArrowUp, Loader2, AlertCircle, Lightbulb } from "lucide-react";
import { useSession } from "../auth/useSession";
import { 
  AgentMemoryRecord,
  clearSessionMemory,
  disableMemory,
  getSessionMemorySummary,
  listMemories,
  promoteSessionMemory,
  SessionMemorySummary
} from "../../lib/memoryApi";
import { SkeletonMetricCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/ARIALiveRegion";
import { useConfirm } from "../../components/ConfirmDialog";
import { getStatusLabel } from "../../app/ui";
import "./MemoryPageV2.css";

export function MemoryPageV2() {
  const { sessionToken } = useSession();
  const [summary, setSummary] = useState<SessionMemorySummary | null>(null);
  const [memories, setMemories] = useState<AgentMemoryRecord[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "clearing" | "promoting" | "disabling">("idle");
  const [actionError, setActionError] = useState<string | null>(null);
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  const { confirm, ConfirmDialog } = useConfirm();
  
  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const [nextSummary, nextMemories] = await Promise.all([
        getSessionMemorySummary(sessionToken),
        listMemories(sessionToken)
      ]);
      setSummary(nextSummary);
      setMemories(Array.isArray(nextMemories.items) ? nextMemories.items : []);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "加载失败");
    }
  }, [sessionToken]);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  const handleClear = useCallback(async () => {
    if (!sessionToken) return;
    
    // 显示确认对话框
    const confirmed = await confirm({
      title: "清空会话记忆",
      message: "此操作将清空所有会话记忆，数据将无法恢复。是否继续？",
      confirmText: "确认清空",
      cancelText: "取消",
      danger: true,
    });
    
    if (!confirmed) return;
    
    setActionState("clearing");
    setActionError(null);
    try {
      await clearSessionMemory(sessionToken);
      await refresh();
      announcePolite("会话记忆已清空");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "清空失败";
      setActionError(errorMsg);
      announcePolite(`清空失败: ${errorMsg}`);
    } finally {
      setActionState("idle");
    }
  }, [sessionToken, refresh, confirm, announcePolite]);
  
  const handlePromote = useCallback(async () => {
    if (!sessionToken) return;
    
    // 显示确认对话框
    const confirmed = await confirm({
      title: "提升为长期记忆",
      message: "将当前会话记忆提升为长期记忆，可在未来任务中复用。",
      confirmText: "确认提升",
      cancelText: "取消",
      danger: false,
    });
    
    if (!confirmed) return;
    
    setActionState("promoting");
    setActionError(null);
    try {
      await promoteSessionMemory(sessionToken);
      await refresh();
      announcePolite("会话记忆已提升为长期记忆");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "提升失败";
      setActionError(errorMsg);
      announcePolite(`提升失败: ${errorMsg}`);
    } finally {
      setActionState("idle");
    }
  }, [sessionToken, refresh, confirm, announcePolite]);
  
  const handleDisable = useCallback(async (memoryId: string) => {
    if (!sessionToken) return;
    
    // 显示确认对话框
    const confirmed = await confirm({
      title: "停用记忆",
      message: `停用记忆 "${memoryId.slice(0, 8)}..." 后，该记忆将不再被使用。`,
      confirmText: "确认停用",
      cancelText: "取消",
      danger: true,
    });
    
    if (!confirmed) return;
    
    setActionState("disabling");
    setActionError(null);
    try {
      await disableMemory(memoryId, sessionToken);
      await refresh();
      announcePolite("记忆已停用");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "停用失败";
      setActionError(errorMsg);
      announcePolite(`停用失败: ${errorMsg}`);
    } finally {
      setActionState("idle");
    }
  }, [sessionToken, refresh, confirm, announcePolite]);
  
  const activeCount = memories.filter(m => m.status.toLowerCase() === "active").length;
  
  if (!sessionToken) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">
          <p>当前未登录</p>
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
          <div className="page-eyebrow">连续性</div>
          <h1 className="page-title-v2">记忆</h1>
          <p className="page-description-v2">
            把会话经验沉淀为可复用的长期上下文
          </p>
        </div>
        <button 
          className="refresh-btn"
          onClick={refresh}
          disabled={status === "loading"}
          aria-busy={status === "loading"}
        >
          {status === "loading" ? (
            <Loader2 size={18} className="spin" />
          ) : (
            <RefreshCw size={18} />
          )}
          刷新
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
          <div className="metric-card-v2" style={{ '--card-color': 'var(--accent-pink)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(236, 72, 153, 0.15)', color: 'var(--accent-pink)' }}>
              <Brain size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">会话条目</p>
              <h3 className="metric-value-v2">{summary?.entry_count || 0}</h3>
            </div>
          </div>
          <div className="metric-card-v2" style={{ '--card-color': 'var(--success)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)' }}>
              <Brain size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">启用记忆</p>
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
              会话记忆
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
                {actionState === "clearing" ? "清空中..." : "清空"}
              </button>
              <button 
                type="button"
                className="action-btn primary"
                onClick={handlePromote}
                disabled={actionState !== "idle"}
                aria-busy={actionState === "promoting"}
              >
                <ArrowUp size={16} />
                {actionState === "promoting" ? "提升中..." : "提升"}
              </button>
            </div>
          </div>
          
          {status === "loading" && !summary ? (
            <div className="loading-state-v2">
              <Loader2 size={24} className="spin" />
              <p>加载中...</p>
            </div>
          ) : summary ? (
            <div className="memory-content">
              <p className="memory-summary">{summary.summary_text || "暂无会话摘要"}</p>
              <div className="memory-meta">
                <span>条目: {summary.entry_count}</span>
                {summary.summary_digest && (
                  <span>摘要指纹: {summary.summary_digest}</span>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-state-v2 memory-empty">
              <Lightbulb size={48} />
              <p>还没有会话摘要</p>
              <span>执行任务后，系统会自动生成会话摘要</span>
            </div>
          )}
        </div>
        
        {memories.length > 0 && (
          <div className="section-card-v2">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <Brain size={20} />
                长期记忆
              </h3>
            </div>
            <div className="memory-list">
              {memories.map((memory) => (
                <div key={memory.memory_id} className="memory-item">
                  <div className="memory-item-header">
                    <span className="memory-id">{memory.memory_id}</span>
                    <span className={`memory-status ${memory.status.toLowerCase()}`}>
                      {getStatusLabel(memory.status)}
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
                      {actionState === "disabling" ? "停用中..." : "停用"}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
