import { Link } from "react-router-dom";

import { resolveApiUrl, ARTIFACT_PATHS } from "../../lib/api";
import { useI18n } from "../../app/locale";
import type { VideoThreadIterationDetailResult } from "../../lib/videoThreadsApi";
import "./VideoThreadWorkbench.css";

function taskIdFromVideoResource(resource: string | null | undefined): string | null {
  if (!resource) {
    return null;
  }
  const match = /^video-task:\/\/([^/]+)\//.exec(resource);
  return match?.[1] ?? null;
}

type VersionTimelineProps = {
  results: VideoThreadIterationDetailResult[];
  selectedResultId: string | null;
  selectingResultId: string | null;
  onSelectResult: (resultId: string) => void;
};

export function VersionTimeline({
  results,
  selectedResultId,
  selectingResultId,
  onSelectResult,
}: VersionTimelineProps) {
  const { t } = useI18n();
  return (
    <section
      aria-label={t("thread.timeline.ariaLabel")}
      className="version-timeline video-thread-workbench__panel video-thread-workbench__panel--tone-neutral video-thread-workbench__panel--emphasis-primary video-thread-workbench__panel--open"
    >
      <div className="version-timeline__header">
        <div>
          <h2>{t("thread.timeline.title")}</h2>
          <p>{t("thread.timeline.description")}</p>
        </div>
      </div>

      <div className="version-timeline__list">
        {results.length ? (
          results.map((result) => {
            const taskId = taskIdFromVideoResource(result.video_resource);
            const isSelected = result.result_id === selectedResultId || result.selected;
            const videoDownloadHref = taskId ? ARTIFACT_PATHS.video(taskId) : null;
            const scriptDownloadHref = taskId ? ARTIFACT_PATHS.script(taskId) : null;

            return (
              <article
                key={result.result_id}
                className={`version-timeline__card ${
                  isSelected ? "version-timeline__card--selected" : ""
                }`}
              >
                <div className="video-thread-workbench__turn-row">
                  <strong>{result.result_id}</strong>
                  <span>{isSelected ? t("thread.timeline.currentVersion") : result.status}</span>
                </div>
                {result.result_summary ? <p>{result.result_summary}</p> : null}
                <div className="video-thread-workbench__intent-meta">
                  {taskId ? (
                    <span className="video-thread-workbench__meta">
                      {t("common.task")}: {taskId}
                    </span>
                  ) : null}
                  <span className="video-thread-workbench__meta">
                    {t("common.status")}:{" "}
                    {isSelected ? t("thread.timeline.currentVersion") : result.status}
                  </span>
                </div>
                <div className="version-timeline__actions">
                  {isSelected ? (
                    <span className="video-thread-workbench__chip">
                      {t("thread.timeline.currentVersionBadge")}
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="video-thread-workbench__action"
                      onClick={() => onSelectResult(result.result_id)}
                      disabled={selectingResultId === result.result_id}
                      aria-label={`${t("thread.timeline.setCurrentVersion")} ${result.result_id}`}
                    >
                      {t("thread.timeline.setCurrentVersion")}
                    </button>
                  )}
                  {taskId ? (
                    <Link
                      to={`/tasks/${encodeURIComponent(taskId)}`}
                      aria-label={`${t("thread.timeline.openTaskDetail")} ${result.result_id}`}
                    >
                      {t("thread.timeline.openTaskDetail")}
                    </Link>
                  ) : null}
                  {videoDownloadHref ? (
                    <a
                      href={resolveApiUrl(videoDownloadHref) ?? undefined}
                      aria-label={`${t("thread.timeline.downloadVideo")} ${result.result_id}`}
                    >
                      {t("thread.timeline.downloadVideo")}
                    </a>
                  ) : null}
                  {scriptDownloadHref ? (
                    <a
                      href={resolveApiUrl(scriptDownloadHref) ?? undefined}
                      aria-label={`${t("thread.timeline.downloadScript")} ${result.result_id}`}
                    >
                      {t("thread.timeline.downloadScript")}
                    </a>
                  ) : null}
                </div>
              </article>
            );
          })
        ) : (
          <p className="video-thread-workbench__meta">{t("thread.timeline.empty")}</p>
        )}
      </div>
    </section>
  );
}
