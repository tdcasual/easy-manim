import { useEffect, useState, useCallback, memo, useRef } from "react";
import { Link } from "react-router-dom";
import { 
  Play, 
  Grid3X3, 
  List,
  RefreshCw,
  Loader2,
  ArrowRight,
  AlertCircle
} from "lucide-react";
import { useSession } from "../auth/useSession";
import { listRecentVideos, RecentVideoItem } from "../../lib/videosApi";
import { resolveApiUrl } from "../../lib/api";
import { SkeletonCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/ARIALiveRegion";
import "./VideosPageV2.css";

const VideoGridCard = memo(function VideoGridCard({ video }: { video: RecentVideoItem }) {
  const videoUrl = resolveApiUrl(video.latest_video_url);
  const previewUrl = resolveApiUrl(video.latest_preview_url);
  const displayTitle = video.display_title || video.task_id;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  
  // 使用 CSS 变量获取状态颜色
  const statusConfig: Record<string, { colorVar: string; label: string }> = {
    completed: { colorVar: 'var(--success)', label: '已完成' },
    rendering: { colorVar: 'var(--accent-blue)', label: '渲染中' },
    running: { colorVar: 'var(--accent-cyan)', label: '执行中' },
    queued: { colorVar: 'var(--warning)', label: '排队中' },
    failed: { colorVar: 'var(--error)', label: '失败' },
  };
  
  const status = statusConfig[video.status.toLowerCase()] || { colorVar: 'var(--text-muted)', label: video.status };
  
  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    
    if (video.paused) {
      video.play().then(() => setIsPlaying(true)).catch(() => {});
    } else {
      video.pause();
      setIsPlaying(false);
    }
  }, []);
  
  const handleMouseEnter = useCallback(() => {
    // 不再自动播放，需要用户主动点击
  }, []);
  
  const handleMouseLeave = useCallback(() => {
    // 不再自动暂停
  }, []);
  
  const handleVideoEnded = useCallback(() => {
    setIsPlaying(false);
  }, []);
  
  return (
    <div className="video-grid-card">
      <div className="video-grid-preview">
        {videoUrl ? (
          <>
            <video
              ref={videoRef}
              poster={previewUrl || undefined}
              preload="metadata"
              muted
              loop
              aria-label={`视频: ${displayTitle}`}
              onEnded={handleVideoEnded}
              onMouseEnter={handleMouseEnter}
              onMouseLeave={handleMouseLeave}
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
          <img src={previewUrl} alt={displayTitle} />
        ) : (
          <div className="video-grid-placeholder">
            <Play size={40} />
          </div>
        )}
        <div className="video-grid-overlay">
          <Link 
            to={`/tasks/${encodeURIComponent(video.task_id)}`} 
            className="video-grid-play"
            aria-label={`打开视频详情: ${displayTitle}`}
          >
            <Play size={24} fill="currentColor" />
          </Link>
        </div>
        <div 
          className="video-grid-status" 
          style={{ background: `${status.colorVar}20`, color: status.colorVar }}
        >
          {status.label}
        </div>
      </div>
      <div className="video-grid-info">
        <h4>{displayTitle}</h4>
        <p>{video.task_id}</p>
        <Link to={`/tasks/${encodeURIComponent(video.task_id)}`} className="video-grid-link">
          查看详情 <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
});

export function VideosPageV2() {
  const { sessionToken } = useSession();
  const [items, setItems] = useState<RecentVideoItem[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  
  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const response = await listRecentVideos(sessionToken, 24);
      setItems(Array.isArray(response.items) ? response.items : []);
      setStatus("idle");
      announcePolite(`已加载 ${response.items?.length || 0} 个视频`);
    } catch (err) {
      setStatus("error");
      const errorMsg = err instanceof Error ? err.message : "加载失败";
      setError(errorMsg);
      announcePolite(`加载失败: ${errorMsg}`);
    }
  }, [sessionToken, announcePolite]);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  if (!sessionToken) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">当前未登录</div>
      </div>
    );
  }
  
  return (
    <div className="page-v2">
      {/* ARIA Live 区域 */}
      <ARIALiveRegion />
      
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">视频库</div>
          <h1 className="page-title-v2">视频</h1>
          <p className="page-description-v2">
            集中回看最近可直接播放的生成结果，用展示标题快速定位内容
          </p>
        </div>
        <div className="page-header-actions">
          <div className="view-toggle" role="group" aria-label="视图切换">
            <button 
              type="button"
              className={viewMode === 'grid' ? 'active' : ''}
              onClick={() => setViewMode('grid')}
              aria-label="网格视图"
              aria-pressed={viewMode === 'grid'}
            >
              <Grid3X3 size={18} />
            </button>
            <button 
              type="button"
              className={viewMode === 'list' ? 'active' : ''}
              onClick={() => setViewMode('list')}
              aria-label="列表视图"
              aria-pressed={viewMode === 'list'}
            >
              <List size={18} />
            </button>
          </div>
          <button 
            type="button"
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
      </div>
      
      {error && (
        <div className="form-error-v2" role="alert">
          <AlertCircle size={16} />
          {error}
        </div>
      )}
      
      {status === "loading" && items.length === 0 ? (
        <div className="videos-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : items.length > 0 ? (
        <div className={`videos-${viewMode}`}>
          {items.map((video) => (
            <VideoGridCard key={video.task_id} video={video} />
          ))}
        </div>
      ) : (
        <div className="empty-state-v2">
          <p>还没有可播放的视频</p>
          <span>先去任务页创建几个任务</span>
        </div>
      )}
    </div>
  );
}
