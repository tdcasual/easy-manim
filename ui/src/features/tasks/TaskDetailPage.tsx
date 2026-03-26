import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getStatusLabel, MetricChip, PageIntro, SectionPanel, StatusPill } from "../../app/ui";
import { resolveApiUrl } from "../../lib/api";
import { cancelTask, getTask, getTaskResult, retryTask, reviseTask, TaskResult, TaskSnapshot } from "../../lib/tasksApi";
import { useSession } from "../auth/useSession";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function TaskDetailPage() {
  const { taskId } = useParams();
  const { sessionToken } = useSession();
  const [snapshot, setSnapshot] = useState<TaskSnapshot | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionState, setActionState] = useState<"idle" | "revise" | "retry" | "cancel">("idle");

  useEffect(() => {
    if (!taskId) return;
    const id = taskId;
    let cancelled = false;
    let timer: number | null = null;
    let attempt = 0;

    async function loadOnce() {
      if (!sessionToken) return;
      try {
        const nextSnapshot = await getTask(id, sessionToken);
        if (cancelled) return;
        setSnapshot(nextSnapshot);

        const nextResult = await getTaskResult(id, sessionToken);
        if (cancelled) return;
        setResult(nextResult);

        if (!TERMINAL.has(String(nextSnapshot.status))) {
          const delay = Math.min(250 * 2 ** attempt, 5000);
          attempt += 1;
          timer = window.setTimeout(loadOnce, delay);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "task_load_failed");
      }
    }

    loadOnce();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [reloadTick, sessionToken, taskId]);

  async function onRevise() {
    if (!taskId || !sessionToken) return;
    const trimmed = feedback.trim();
    if (!trimmed) return;

    setActionState("revise");
    setActionError(null);
    try {
      await reviseTask(taskId, trimmed, sessionToken);
      setFeedback("");
      setReloadTick((tick) => tick + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "task_revise_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onRetry() {
    if (!taskId || !sessionToken) return;

    setActionState("retry");
    setActionError(null);
    try {
      await retryTask(taskId, sessionToken);
      setReloadTick((tick) => tick + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "task_retry_failed");
    } finally {
      setActionState("idle");
    }
  }

  async function onCancel() {
    if (!taskId || !sessionToken) return;

    setActionState("cancel");
    setActionError(null);
    try {
      await cancelTask(taskId, sessionToken);
      setReloadTick((tick) => tick + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "task_cancel_failed");
    } finally {
      setActionState("idle");
    }
  }

  if (!taskId) {
    return (
      <section className="page">
        <h2>任务详情</h2>
        <p className="muted">缺少任务 ID。</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="page">
        <h2>任务详情</h2>
        <p className="muted">加载失败：{error}</p>
      </section>
    );
  }

  if (!snapshot) {
    return (
      <section className="page">
        <h2>任务详情</h2>
        <p className="muted">正在加载…</p>
      </section>
    );
  }

  const status = String(snapshot.status);
  const phase = String(snapshot.phase);
  const terminal = TERMINAL.has(status);
  const validationSummary = snapshot.latest_validation_summary?.summary || result?.summary || "暂时还没有校验结论。";
  const videoUrl = resolveApiUrl(result?.video_download_url);
  const previewUrls = Array.isArray(result?.preview_download_urls)
    ? result.preview_download_urls.map((url) => resolveApiUrl(url)).filter((url): url is string => Boolean(url))
    : [];
  const resourceLabel =
    result?.video_download_url?.split("/").slice(-1)[0] || result?.video_resource?.split("/").slice(-1)[0] || null;
  const outcomeMessage = result?.ready
    ? "最新产出已经就绪，可以直接回看视频。"
    : terminal
      ? "任务已经结束，但当前没有可播放的最终视频。"
      : "系统仍在生成或校验这一轮结果。";

  return (
    <section className="page page--detail">
      <PageIntro
        eyebrow="任务"
        title="任务详情"
        description="查看当前产出，直接回看视频，并通过精确的中文修订说明继续推动同一条工作链路。"
        actions={
          <div className="inlineActions">
            <button className="button buttonQuiet" type="button" onClick={() => setReloadTick((tick) => tick + 1)}>
              刷新详情
            </button>
            <Link className="button buttonQuiet" to="/tasks">
              返回任务列表
            </Link>
          </div>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="状态" value={<StatusPill value={status} compact />} />
            <MetricChip label="阶段" value={getStatusLabel(phase)} />
            <MetricChip label="尝试次数" value={snapshot.attempt_count ?? 0} />
          </div>
        }
      />

      <div className="identityBand">
        <div>
          <span className="muted small">任务 ID</span>
          <div className="identityCode">{snapshot.task_id}</div>
        </div>
        <div className="identityBandMeta">
          <span className="muted small">当前产出</span>
          <p>{outcomeMessage}</p>
        </div>
      </div>

      <div className="pageSplit">
        <SectionPanel title="操作" detail="提交修订说明、重试失败任务，或在仍在执行时取消当前任务。">
          <label className="field">
            <span className="fieldLabel">修订说明</span>
            <textarea
              aria-label="修订说明"
              className="textarea"
              rows={5}
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
              placeholder="例如：改成蓝色、字幕改为中文、放慢节奏、增加标题说明…"
            />
          </label>

          <div className="buttonRow">
            <button className="button buttonPrimary" type="button" onClick={onRevise} disabled={actionState !== "idle"}>
              {actionState === "revise" ? "正在提交…" : "提交修订"}
            </button>
            {status.toLowerCase() === "failed" ? (
              <button className="button" type="button" onClick={onRetry} disabled={actionState !== "idle"}>
                {actionState === "retry" ? "正在重试…" : "失败重试"}
              </button>
            ) : null}
            {!terminal ? (
              <button className="button buttonDanger" type="button" onClick={onCancel} disabled={actionState !== "idle"}>
                {actionState === "cancel" ? "正在取消…" : "取消任务"}
              </button>
            ) : null}
          </div>

          {actionError ? (
            <p role="alert" className="alert">
              {actionError}
            </p>
          ) : null}
        </SectionPanel>

        <SectionPanel title="结果" detail="查看最新视频、校验结论，以及当前这轮任务的资源情况。">
          {result ? (
            <div className="resultStack">
              {videoUrl ? (
                <div className="mediaStage">
                  <video
                    className="videoPlayer videoPlayer--detail"
                    controls
                    playsInline
                    preload="metadata"
                    poster={previewUrls[0]}
                    src={videoUrl}
                  />
                  <div className="inlineActions">
                    <a className="button buttonQuiet" href={videoUrl} target="_blank" rel="noreferrer">
                      打开视频
                    </a>
                  </div>
                </div>
              ) : previewUrls[0] ? (
                <div className="mediaStage">
                  <img className="mediaPreview" src={previewUrls[0]} alt={`${snapshot.task_id} 预览帧`} />
                </div>
              ) : null}

              <div className="infoBlock">
                <span className="infoLabel">结果摘要</span>
                <p className="infoValue">{String(result.summary ?? "") || "暂时还没有结果摘要。"}</p>
              </div>
              <div className="infoBlock">
                <span className="infoLabel">校验结论</span>
                <p className="infoValue">{validationSummary}</p>
              </div>
              <div className="infoBlock">
                <span className="infoLabel">视频资源</span>
                {videoUrl && resourceLabel ? (
                  <a href={videoUrl} className="resourceLink" target="_blank" rel="noreferrer">
                    {resourceLabel}
                  </a>
                ) : resourceLabel ? (
                  <span className="muted">{resourceLabel}</span>
                ) : (
                  <span className="muted">还没有可播放的视频资源。</span>
                )}
              </div>
            </div>
          ) : (
            <p className="muted">正在加载结果…</p>
          )}
        </SectionPanel>
      </div>

      <div className="pageSplit pageSplit--facts">
        <SectionPanel title="运行信息" detail="当前任务状态、阶段与尝试次数的简洁读数。">
          <dl className="factsGrid">
            <dt className="muted">状态</dt>
            <dd>{getStatusLabel(status)}</dd>
            <dt className="muted">阶段</dt>
            <dd>{getStatusLabel(phase)}</dd>
            <dt className="muted">尝试次数</dt>
            <dd>{String(snapshot.attempt_count ?? 0)}</dd>
          </dl>
        </SectionPanel>

        <SectionPanel title="操作建议" detail="内容问题优先修订，偶发失败再重试，这样更容易定位有效变化。">
          <p className="panelParagraph">
            {terminal
              ? "当前任务已经进入终态。如果视频已生成，可直接回看；如果结果不满意，建议发起一次针对性的修订。"
              : "当前任务仍在执行中。详情页会持续轮询，直到状态稳定下来。"}
          </p>
        </SectionPanel>
      </div>
    </section>
  );
}
