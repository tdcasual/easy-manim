import { useEffect, useId, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { 
  Plus, 
  RefreshCw, 
  Play, 
  ArrowRight,
  Clock,
  CheckCircle2,
  XCircle,
  Sparkles,
  Loader2
} from "lucide-react";
import { useSession } from "../auth/useSession";
import { createTask, listTasks, TaskListItem } from "../../lib/tasksApi";
import { listRecentVideos, RecentVideoItem } from "../../lib/videosApi";
import { resolveApiUrl } from "../../lib/api";
import { SkeletonCard, SkeletonMetricCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/ARIALiveRegion";
import "./TasksPageV2.css";

const QUICK_PROMPTS = [
  "画一个蓝色圆形，并保持画面干净简洁",
  "制作一个带中文标签的正弦波动画",
  "做一个对比季度营收的柱状图，适合中文演示"
] as const;

function MetricCard({ 
  label, 
  value, 
  icon: Icon, 
  color,
  trend 
}: { 
  label: string; 
  value: number | string; 
  icon: React.ElementType;
  color: string;
  trend?: { value: number; positive: boolean };
}) {
  return (
    <div className="metric-card-v2" style={{ '--card-color': color } as React.CSSProperties}>
      <div className="metric-icon-wrapper" style={{ background: `${color}20`, color }}>
        <Icon size={20} />
      </div>
      <div className="metric-content">
        <p className="metric-label-v2">{label}</p>
        <h3 className="metric-value-v2">{value}</h3>
        {trend && (
          <span className={`metric-trend ${trend.positive ? 'positive' : 'negative'}`}>
            {trend.positive ? '+' : ''}{trend.value}%
          </span>
        )}
      </div>
      <div className="metric-glow" style={{ background: color }} />
    </div>
  );
}

function VideoCard({ video }: { video: RecentVideoItem }) {
  const videoUrl = resolveApiUrl(video.latest_video_url);
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const displayTitle = video.display_title || video.task_id;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  
  // 使用 CSS 变量替代硬编码颜色
  const statusConfig: Record<string, { colorVar: string; label: string }> = {
    completed: { colorVar: 'var(--success)', label: '已完成' },
    rendering: { colorVar: 'var(--accent-blue)', label: '渲染中' },
    running: { colorVar: 'var(--accent-cyan)', label: '执行中' },
    queued: { colorVar: 'var(--warning)', label: '排队中' },
    failed: { colorVar: 'var(--error)', label: '失败' },
  };
  
  const status = statusConfig[video.status.toLowerCase()] || { colorVar: 'var(--text-muted)', label: video.status };
  
  const togglePlay = useCallback(() => {
    const videoEl = videoRef.current;
    if (!videoEl) return;
    
    if (videoEl.paused) {
      videoEl.play().then(() => setIsPlaying(true)).catch(() => {});
    } else {
      videoEl.pause();
      setIsPlaying(false);
    }
  }, []);
  
  const handleVideoEnded = useCallback(() => {
    setIsPlaying(false);
  }, []);
  
  return (
    <div className="video-card-v2">
      <div className="video-preview-wrapper">
        {videoUrl ? (
          <>
            <video
              ref={videoRef}
              className="video-preview-v2"
              poster={previewUrl || undefined}
              preload="metadata"
              muted
              loop
              aria-label={`视频: ${displayTitle}`}
              onEnded={handleVideoEnded}
            >
              <source src={videoUrl} />
            </video>
            {/* 播放/暂停控制按钮 */}
            <button
              type="button"
              className={`video-play-control ${isPlaying ? 'playing' : ''}`}
              onClick={togglePlay}
              aria-label={isPlaying ? '暂停视频' : '播放视频'}
              aria-pressed={isPlaying}
            >
              {isPlaying ? (
                <span className="video-control-icon pause">
                  <span className="pause-bar" />
                  <span className="pause-bar" />
                </span>
              ) : (
                <Play size={20} fill="currentColor" />
              )}
            </button>
          </>
        ) : previewUrl ? (
          <img src={previewUrl} alt={displayTitle} className="video-preview-v2" />
        ) : (
          <div className="video-placeholder">
            <Play size={32} />
          </div>
        )}
        <div 
          className="video-status-badge" 
          style={{ background: `${status.colorVar}20`, color: status.colorVar }}
        >
          {status.label}
        </div>
      </div>
      <div className="video-info-v2">
        <h4 className="video-title-v2">{displayTitle}</h4>
        <p className="video-id-v2">{video.task_id}</p>
        <p className="video-summary-v2">
          {video.latest_summary || "视频已生成，可继续查看任务详情或发起修订。"}
        </p>
        <div className="video-actions-v2">
          <Link to={`/tasks/${encodeURIComponent(video.task_id)}`} className="video-action-btn primary">
            查看详情
          </Link>
          {videoUrl && (
            <a 
              href={videoUrl} 
              target="_blank" 
              rel="noreferrer" 
              className="video-action-btn"
            >
              打开视频
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function TaskRow({ task, index }: { task: TaskListItem; index: number }) {
  // 使用 CSS 变量替代硬编码颜色
  const statusConfig: Record<string, { colorVar: string; label: string }> = {
    completed: { colorVar: 'var(--success)', label: '已完成' },
    rendering: { colorVar: 'var(--accent-blue)', label: '渲染中' },
    running: { colorVar: 'var(--accent-cyan)', label: '执行中' },
    queued: { colorVar: 'var(--warning)', label: '排队中' },
    failed: { colorVar: 'var(--error)', label: '失败' },
  };
  
  const status = statusConfig[task.status.toLowerCase()] || { 
    colorVar: 'var(--text-muted)', 
    label: task.status 
  };
  
  const displayTitle = task.display_title || task.task_id;
  
  return (
    <Link 
      to={`/tasks/${encodeURIComponent(task.task_id)}`}
      className="task-row"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="task-row-content">
        <div className="task-row-title">{displayTitle}</div>
        <div className="task-row-meta">
          <span className="task-row-id">{task.task_id}</span>
        </div>
      </div>
      <div 
        className="task-row-status"
        style={{ background: `${status.colorVar}15`, color: status.colorVar }}
      >
        <span className="status-dot-v2" style={{ background: status.colorVar }} />
        {status.label}
      </div>
      <ArrowRight size={16} className="task-row-arrow" />
    </Link>
  );
}

export function TasksPageV2() {
  const { sessionToken } = useSession();
  const promptId = useId();
  
  const [prompt, setPrompt] = useState("");
  const [items, setItems] = useState<TaskListItem[]>([]);
  const [recentVideos, setRecentVideos] = useState<RecentVideoItem[]>([]);
  const [loadingState, setLoadingState] = useState<"idle" | "loading" | "error">("idle");
  const [videoState, setVideoState] = useState<"idle" | "loading">("idle");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const refreshRecentVideos = useCallback(async (token: string) => {
    setVideoState("loading");
    try {
      const response = await listRecentVideos(token, 6);
      setRecentVideos(Array.isArray(response.items) ? response.items : []);
    } catch {
      setRecentVideos([]);
    } finally {
      setVideoState("idle");
    }
  }, []);
  
  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    setLoadingState("loading");
    setError(null);
    try {
      const response = await listTasks(sessionToken);
      setItems(Array.isArray(response.items) ? response.items : []);
      setLoadingState("idle");
      void refreshRecentVideos(sessionToken);
    } catch (err) {
      setLoadingState("error");
      setError(err instanceof Error ? err.message : "task_list_failed");
    }
  }, [sessionToken, refreshRecentVideos]);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  async function onCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!sessionToken) return;
    const trimmed = prompt.trim();
    if (!trimmed) return;
    
    setCreating(true);
    setError(null);
    try {
      const created = await createTask(trimmed, sessionToken);
      setPrompt("");
      if (created?.task_id) {
        setItems(prev => [{
          task_id: created.task_id,
          status: "queued",
          display_title: created.display_title ?? trimmed,
          title_source: created.title_source ?? "prompt"
        }, ...prev]);
        announcePolite(`任务已创建: ${created.display_title ?? trimmed}`);
      }
      await refresh();
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "task_create_failed";
      setError(errorMsg);
      announcePolite(`创建失败: ${errorMsg}`);
    } finally {
      setCreating(false);
    }
  }
  
  const completedCount = items.filter(t => t.status.toLowerCase() === "completed").length;
  const activeCount = items.filter(t => 
    !["completed", "failed", "cancelled"].includes(t.status.toLowerCase())
  ).length;
  const failedCount = items.filter(t => t.status.toLowerCase() === "failed").length;
  
  // ARIA 消息通知
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  
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
      {/* ARIA Live 区域 - 用于屏幕阅读器通知 */}
      <ARIALiveRegion />
      
      {/* 页面头部 */}
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">创作台</div>
          <h1 className="page-title-v2">任务管理</h1>
          <p className="page-description-v2">
            用中文描述创作意图，查看最近任务队列，并直接回看最新生成的视频结果
          </p>
        </div>
        <button 
          className="refresh-btn"
          onClick={refresh}
          disabled={loadingState === "loading"}
        >
          {loadingState === "loading" ? (
            <Loader2 size={18} className="spin" />
          ) : (
            <RefreshCw size={18} />
          )}
          刷新列表
        </button>
      </div>
      
      {/* 指标卡片 */}
      {loadingState === "loading" && items.length === 0 ? (
        <div className="metrics-grid-v2">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : (
        <div className="metrics-grid-v2">
          <MetricCard 
            label="进行中" 
            value={activeCount} 
            icon={Clock}
            color="var(--accent-cyan)"
          />
          <MetricCard 
            label="已完成" 
            value={completedCount} 
            icon={CheckCircle2}
            color="var(--success)"
          />
          <MetricCard 
            label="失败" 
            value={failedCount} 
            icon={XCircle}
            color="var(--error)"
          />
          <MetricCard 
            label="总任务" 
            value={items.length} 
            icon={Sparkles}
            color="var(--accent-purple)"
          />
        </div>
      )}
      
      {/* 主内容区 */}
      <div className="content-grid-v2">
        {/* 左侧：创建任务 */}
        <div className="main-column">
          <div className="section-card-v2 create-task-card">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <Plus size={20} />
                新建任务
              </h3>
            </div>
            
            <form onSubmit={onCreate} className="create-task-form">
              <div className="form-group-v2">
                <label className="form-label-v2" htmlFor={promptId}>
                  任务描述
                </label>
                <textarea
                  id={promptId}
                  className="form-textarea-v2"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder='例如："做一个简洁的蓝色圆形动画"或"生成一个带中文标题的柱状图视频"'
                  rows={5}
                  spellCheck={false}
                />
              </div>
              
              <div className="quick-prompts-v2">
                <span className="quick-prompts-label">快速提示：</span>
                <div className="quick-prompts-list">
                  {QUICK_PROMPTS.map((quickPrompt) => (
                    <button
                      key={quickPrompt}
                      type="button"
                      className="quick-prompt-chip"
                      onClick={() => setPrompt(quickPrompt)}
                    >
                      {quickPrompt}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="form-actions-v2">
                <button
                  type="submit"
                  className="submit-btn-v2"
                  disabled={creating || !prompt.trim()}
                >
                  {creating ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      创建中...
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} />
                      创建任务
                    </>
                  )}
                </button>
              </div>
              
              {error && (
                <div className="form-error-v2">{error}</div>
              )}
            </form>
          </div>
          
          {/* 最近任务 */}
          <div className="section-card-v2">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <Clock size={20} />
                最近任务队列
              </h3>
              <Link to="/tasks" className="section-link">查看全部</Link>
            </div>
            
            <div className="task-list-v2">
              {loadingState === "loading" && items.length === 0 ? (
                <>
                  <SkeletonCard />
                  <SkeletonCard />
                  <SkeletonCard />
                </>
              ) : items.length > 0 ? (
                items.slice(0, 8).map((task, index) => (
                  <TaskRow key={task.task_id} task={task} index={index} />
                ))
              ) : (
                <div className="empty-state-v2">
                  <p>还没有任务</p>
                  <span>从上方创建您的第一个任务</span>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* 右侧：最近视频 */}
        <div className="side-column">
          <div className="section-card-v2 video-section">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <Play size={20} />
                最近视频
              </h3>
              <Link to="/videos" className="section-link">查看全部</Link>
            </div>
            
            {videoState === "loading" && recentVideos.length === 0 ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : recentVideos.length > 0 ? (
              <div className="video-list-v2">
                {recentVideos.map((video) => (
                  <VideoCard key={video.task_id} video={video} />
                ))}
              </div>
            ) : (
              <div className="empty-state-v2">
                <p>还没有视频</p>
                <span>创建任务后将在此显示</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
