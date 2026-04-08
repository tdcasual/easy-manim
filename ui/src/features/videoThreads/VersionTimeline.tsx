import { Link } from "react-router-dom";

import { resolveApiUrl } from "../../lib/api";
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
  return (
    <section
      aria-label="Versions"
      className="version-timeline video-thread-workbench__panel video-thread-workbench__panel--tone-neutral video-thread-workbench__panel--emphasis-primary video-thread-workbench__panel--open"
    >
      <div className="version-timeline__header">
        <div>
          <h2>Versions</h2>
          <p>
            Compare visible results for this iteration, switch the current version, or open the
            source task.
          </p>
        </div>
      </div>

      <div className="version-timeline__list">
        {results.length ? (
          results.map((result) => {
            const taskId = taskIdFromVideoResource(result.video_resource);
            const isSelected = result.result_id === selectedResultId || result.selected;
            const videoDownloadHref = taskId
              ? `/api/tasks/${encodeURIComponent(taskId)}/artifacts/final_video.mp4`
              : null;
            const scriptDownloadHref = taskId
              ? `/api/tasks/${encodeURIComponent(taskId)}/artifacts/current_script.py`
              : null;

            return (
              <article
                key={result.result_id}
                className={`version-timeline__card ${
                  isSelected ? "version-timeline__card--selected" : ""
                }`}
              >
                <div className="video-thread-workbench__turn-row">
                  <strong>{result.result_id}</strong>
                  <span>{isSelected ? "current version" : result.status}</span>
                </div>
                {result.result_summary ? <p>{result.result_summary}</p> : null}
                <div className="video-thread-workbench__intent-meta">
                  {taskId ? (
                    <span className="video-thread-workbench__meta">Task: {taskId}</span>
                  ) : null}
                  <span className="video-thread-workbench__meta">
                    Status: {isSelected ? "selected" : result.status}
                  </span>
                </div>
                <div className="version-timeline__actions">
                  {isSelected ? (
                    <span className="video-thread-workbench__chip">Current version</span>
                  ) : (
                    <button
                      type="button"
                      className="video-thread-workbench__action"
                      onClick={() => onSelectResult(result.result_id)}
                      disabled={selectingResultId === result.result_id}
                      aria-label={`Set as current version ${result.result_id}`}
                    >
                      Set as current version
                    </button>
                  )}
                  {taskId ? (
                    <Link
                      to={`/tasks/${encodeURIComponent(taskId)}`}
                      aria-label={`Open task detail for ${result.result_id}`}
                    >
                      Open task detail
                    </Link>
                  ) : null}
                  {videoDownloadHref ? (
                    <a
                      href={resolveApiUrl(videoDownloadHref) ?? undefined}
                      aria-label={`Download video for ${result.result_id}`}
                    >
                      Download video
                    </a>
                  ) : null}
                  {scriptDownloadHref ? (
                    <a
                      href={resolveApiUrl(scriptDownloadHref) ?? undefined}
                      aria-label={`Download script for ${result.result_id}`}
                    >
                      Download script
                    </a>
                  ) : null}
                </div>
              </article>
            );
          })
        ) : (
          <p className="video-thread-workbench__meta">
            No visible versions are available for this iteration yet.
          </p>
        )}
      </div>
    </section>
  );
}
