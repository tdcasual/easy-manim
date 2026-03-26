import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, MetricChip, PageIntro, SectionPanel, StatusPill } from "../../app/ui";
import { resolveApiUrl } from "../../lib/api";
import { createTask, getTaskResult, listTasks } from "../../lib/tasksApi";
import { useSession } from "../auth/useSession";

type TaskListItem = { task_id: string; status: string };
type RecentVideoItem = {
  task_id: string;
  status: string;
  summary: string;
  videoUrl: string;
  previewUrl?: string;
};

const QUICK_PROMPTS = [
  "画一个蓝色圆形，并保持画面干净简洁",
  "制作一个带中文标签的正弦波动画",
  "做一个对比季度营收的柱状图，适合中文演示"
] as const;

export function TasksPage() {
  const { sessionToken } = useSession();
  const promptId = useId();

  const [prompt, setPrompt] = useState("");
  const [items, setItems] = useState<TaskListItem[]>([]);
  const [recentVideos, setRecentVideos] = useState<RecentVideoItem[]>([]);
  const [loadingState, setLoadingState] = useState<"idle" | "loading" | "error">("idle");
  const [videoState, setVideoState] = useState<"idle" | "loading">("idle");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshRecentVideos(taskItems: TaskListItem[], token: string) {
    const candidates = taskItems.slice(0, 8);
    if (!candidates.length) {
      setRecentVideos([]);
      setVideoState("idle");
      return;
    }

    setVideoState("loading");
    const settled = await Promise.allSettled(
      candidates.map(async (task) => {
        const result = await getTaskResult(task.task_id, token);
        const videoUrl = resolveApiUrl(result.video_download_url);
        if (!videoUrl) return null;

        const previewUrls = Array.isArray(result.preview_download_urls)
          ? result.preview_download_urls.map((url) => resolveApiUrl(url)).filter((url): url is string => Boolean(url))
          : [];

        return {
          task_id: task.task_id,
          status: task.status,
          summary: String(result.summary ?? "").trim() || "视频已生成，可继续查看任务详情或发起修订。",
          videoUrl,
          previewUrl: previewUrls[0]
        } satisfies RecentVideoItem;
      })
    );

    setRecentVideos(
      settled.flatMap((item) => {
        if (item.status !== "fulfilled" || !item.value) return [];
        return [item.value];
      })
    );
    setVideoState("idle");
  }

  async function refresh() {
    if (!sessionToken) return;
    setLoadingState("loading");
    setError(null);
    try {
      const response = await listTasks(sessionToken);
      const nextItems = Array.isArray(response.items) ? response.items : [];
      setItems(nextItems);
      setLoadingState("idle");
      void refreshRecentVideos(nextItems, sessionToken);
    } catch (err) {
      setLoadingState("error");
      setError(err instanceof Error ? err.message : "task_list_failed");
    }
  }

  const completedCount = items.filter((task) => String(task.status).toLowerCase() === "completed").length;
  const activeCount = items.filter((task) => {
    const status = String(task.status).toLowerCase();
    return !["completed", "failed", "cancelled"].includes(status);
  }).length;
  const failedCount = items.filter((task) => String(task.status).toLowerCase() === "failed").length;

  useEffect(() => {
    refresh();
    // refresh is intentionally not a dependency; it's stable for our use.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

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
        // Optimistic insert so the operator sees the new id immediately.
        setItems((prev) => [{ task_id: created.task_id, status: "queued" }, ...prev]);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "task_create_failed");
    } finally {
      setCreating(false);
    }
  }

  if (!sessionToken) {
    return (
      <section className="page">
        <h2>任务</h2>
        <p className="muted">当前未登录。</p>
      </section>
    );
  }

  return (
    <section className="page tasksPage">
      <PageIntro
        eyebrow="创作台"
        title="任务"
        description="用中文描述创作意图，查看最近任务队列，并直接回看最新生成的视频结果。"
        actions={
          <button className="button buttonQuiet" type="button" onClick={refresh} disabled={loadingState === "loading"}>
            {loadingState === "loading" ? "正在刷新…" : "刷新列表"}
          </button>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="进行中" value={activeCount} />
            <MetricChip label="已完成" value={completedCount} />
            <MetricChip label="失败" value={failedCount} />
          </div>
        }
      />

      <div className="pageSplit pageSplit--wide">
        <SectionPanel
          title="新建任务"
          detail="先用一句中文描述清楚目标。第一轮出结果后，再针对具体问题继续修订。"
        >
          <form className="stackForm" onSubmit={onCreate} aria-label="create task form">
            <label className="field" htmlFor={promptId}>
              <span className="fieldLabel">任务描述</span>
              <textarea
                id={promptId}
                aria-label="任务描述"
                className="textarea textarea--hero"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder='例如：“做一个简洁的蓝色圆形动画”或“生成一个带中文标题的柱状图视频”'
                rows={7}
                spellCheck={false}
              />
            </label>

            <div className="quickPromptRow">
              {QUICK_PROMPTS.map((quickPrompt) => (
                <button
                  key={quickPrompt}
                  className="quickPrompt"
                  type="button"
                  onClick={() => setPrompt(quickPrompt)}
                >
                  {quickPrompt}
                </button>
              ))}
            </div>

            <div className="buttonRow">
              <button className="button buttonPrimary" type="submit" disabled={creating || prompt.trim().length === 0}>
                {creating ? "正在创建…" : "创建任务"}
              </button>
              <p className="muted small formHint">建议先写核心意图，首轮生成后再补充风格、节奏和细节。</p>
            </div>

            {error ? (
              <p role="alert" className="alert">
                {error}
              </p>
            ) : null}
          </form>
        </SectionPanel>

        <SectionPanel
          title="最近生成的视频"
          detail="优先展示最新可直接播放的结果，适合快速回看、对比和继续微调。"
        >
          {videoState === "loading" && recentVideos.length === 0 ? <p className="muted">正在整理最近视频…</p> : null}

          {recentVideos.length ? (
            <div className="videoGallery" aria-label="recent videos">
              {recentVideos.map((video) => (
                <article key={video.task_id} className="videoCard">
                  <div className="videoFrame">
                    <video
                      className="videoPlayer"
                      controls
                      playsInline
                      preload="metadata"
                      poster={video.previewUrl}
                      src={video.videoUrl}
                    />
                  </div>
                  <div className="videoCardBody">
                    <div className="listTitleRow">
                      <span className="listTitle">{video.task_id}</span>
                      <StatusPill value={String(video.status)} compact />
                    </div>
                    <p className="listCaption">{video.summary}</p>
                    <div className="inlineActions">
                      <Link className="button buttonQuiet" to={`/tasks/${encodeURIComponent(video.task_id)}`}>
                        查看任务
                      </Link>
                      <a className="resourceLink" href={video.videoUrl} target="_blank" rel="noreferrer">
                        打开视频
                      </a>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : videoState === "loading" ? null : (
            <EmptyState
              title="还没有可回看的视频"
              body="先创建几个任务。只要某个任务产出了最终视频，这里就会自动出现可直接播放的最近结果。"
            />
          )}
        </SectionPanel>
      </div>

      <div className="pageSplit">
        <SectionPanel
          title="最近任务队列"
          detail="按最近顺序查看任务。打开后可继续修订、重试或检查输出结果。"
          className="sectionPanel--list"
        >
          {loadingState === "loading" && items.length === 0 ? <p className="muted">正在加载…</p> : null}

          {items.length ? (
            <ul className="listStack" aria-label="task list">
              {items.map((task) => (
                <li key={task.task_id}>
                  <Link className="listLinkRow" to={`/tasks/${encodeURIComponent(task.task_id)}`}>
                    <div className="listPrimary">
                      <span className="listTitle">{task.task_id}</span>
                      <span className="listCaption">打开详情页，查看视频、校验结果和修订入口。</span>
                    </div>
                    <div className="listMeta">
                      <StatusPill value={String(task.status)} />
                      <span className="listChevron" aria-hidden="true">
                        ↗
                      </span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : loadingState === "error" ? (
            <p className="muted">任务列表加载失败。</p>
          ) : (
            <EmptyState
              title="还没有任务"
              body="从一个简短明确的中文描述开始。任务一旦创建，就会立刻出现在这里。"
            />
          )}
        </SectionPanel>

        <SectionPanel title="建议节奏" detail="中文创作场景下，保持小步快跑会更容易得到稳定结果。">
          <ol className="workflowList">
            <li>先提交一个易于验证的简洁目标，不要一开始就堆满所有要求。</li>
            <li>先回看最近视频，再决定要改的是内容、节奏、字幕还是风格。</li>
            <li>每次修订只改一类问题，这样更容易定位真正有效的变化。</li>
          </ol>
        </SectionPanel>
      </div>
    </section>
  );
}
