import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, MetricChip, PageIntro, SectionPanel, StatusPill } from "../../app/ui";
import { resolveApiUrl } from "../../lib/api";
import { listRecentVideos, RecentVideoItem } from "../../lib/videosApi";
import { useSession } from "../auth/useSession";

function readDisplayTitle(item: RecentVideoItem): string {
  return String(item.display_title || "").trim() || item.task_id;
}

export function VideosPage() {
  const { sessionToken } = useSession();
  const [items, setItems] = useState<RecentVideoItem[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const response = await listRecentVideos(sessionToken, 24);
      setItems(Array.isArray(response.items) ? response.items : []);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "recent_videos_load_failed");
    }
  }

  useEffect(() => {
    refresh();
    // refresh is stable for our use.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

  if (!sessionToken) {
    return (
      <section className="page">
        <h2>视频</h2>
        <p className="muted">当前未登录。</p>
      </section>
    );
  }

  return (
    <section className="page page--videos">
      <PageIntro
        eyebrow="视频工作台"
        title="视频"
        description="集中回看最近可直接播放的生成结果，用展示标题快速定位内容，再顺着同一条任务链继续修订。"
        actions={
          <button className="button buttonQuiet" type="button" onClick={refresh} disabled={status === "loading"}>
            {status === "loading" ? "正在刷新…" : "刷新视频"}
          </button>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="最近视频" value={items.length} />
            <MetricChip
              label="可修订"
              value={items.filter((item) => !["failed", "cancelled"].includes(String(item.status).toLowerCase())).length}
            />
            <MetricChip
              label="已完成"
              value={items.filter((item) => String(item.status).toLowerCase() === "completed").length}
            />
          </div>
        }
      />

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "recent_videos_load_failed"}
        </p>
      ) : null}

      <SectionPanel title="最近可播放结果" detail="这里优先展示已经产出最终视频的任务，适合快速回看、对比和继续打磨。">
        {status === "loading" && items.length === 0 ? <p className="muted">正在加载最近视频…</p> : null}

        {items.length ? (
          <div className="videoGallery videoGallery--tiles" aria-label="video list">
            {items.map((item) => {
              const displayTitle = readDisplayTitle(item);
              const videoUrl = resolveApiUrl(item.latest_video_url);
              const previewUrl = resolveApiUrl(item.latest_preview_url);
              return (
                <article key={item.task_id} className="videoCard">
                  <div className="videoFrame">
                    <video
                      className="videoPlayer"
                      controls
                      playsInline
                      preload="metadata"
                      poster={previewUrl || undefined}
                      src={videoUrl || undefined}
                    />
                  </div>
                  <div className="videoCardBody">
                    <div className="listTitleRow">
                      <span className="listTitle">{displayTitle}</span>
                      <StatusPill value={String(item.status)} compact />
                    </div>
                    <div className="metaChips">
                      <span className="metaChip">{item.task_id}</span>
                    </div>
                    <p className="listCaption">
                      {String(item.latest_summary || "").trim() || "最近一轮已经产出视频，可继续进入详情页补充修订。"}
                    </p>
                    <div className="inlineActions">
                      <Link className="button buttonQuiet" to={`/tasks/${encodeURIComponent(item.task_id)}`}>
                        查看详情
                      </Link>
                      <Link className="button buttonPrimary" to={`/tasks/${encodeURIComponent(item.task_id)}`}>
                        继续修订
                      </Link>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : status === "loading" ? null : (
          <EmptyState
            title="还没有可播放的视频"
            body="先去任务页创建几个任务。只要某个任务产出了最终视频，这里就会自动汇总展示。"
            action={
              <Link className="button buttonQuiet" to="/tasks">
                去创建任务
              </Link>
            }
          />
        )}
      </SectionPanel>
    </section>
  );
}
