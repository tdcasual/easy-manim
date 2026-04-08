import { type TaskResult } from "../../lib/tasksApi";
import { resolveApiUrl } from "../../lib/api";
import type {
  VideoThreadIterationDetailResult,
  VideoThreadSurface,
} from "../../lib/videoThreadsApi";

type SelectedVersionHeroProps = {
  surface: VideoThreadSurface;
  selectedIterationId: string | null;
  selectedResult: VideoThreadIterationDetailResult | null;
  selectedTaskId: string | null;
  downloads: TaskResult | null;
  downloadError: string | null;
};

export function SelectedVersionHero({
  surface,
  selectedIterationId,
  selectedResult,
  selectedTaskId,
  downloads,
  downloadError,
}: SelectedVersionHeroProps) {
  const videoDownloadHref =
    downloads?.video_download_url ??
    (selectedTaskId
      ? `/api/tasks/${encodeURIComponent(selectedTaskId)}/artifacts/final_video.mp4`
      : null);
  const scriptDownloadHref =
    downloads?.script_download_url ??
    (selectedTaskId
      ? `/api/tasks/${encodeURIComponent(selectedTaskId)}/artifacts/current_script.py`
      : null);
  const validationReportDownloadHref =
    downloads?.validation_report_download_url ??
    (selectedTaskId
      ? `/api/tasks/${encodeURIComponent(selectedTaskId)}/artifacts/validations/validation_report_v1.json`
      : null);
  const summary =
    selectedResult?.result_summary ??
    surface.current_focus.current_result_summary ??
    "No selected version has been projected yet.";

  return (
    <section aria-label="Selected version">
      <h2>Selected version</h2>
      <p>{summary}</p>
      <p>
        Selected result:{" "}
        {selectedResult?.result_id ?? surface.current_focus.current_result_id ?? "none"}
      </p>
      <p>
        Selected iteration:{" "}
        {selectedIterationId ?? surface.current_focus.current_iteration_id ?? "none"}
      </p>
      {selectedTaskId ? <p>Source task: {selectedTaskId}</p> : null}
      <div>
        {videoDownloadHref ? (
          <a href={resolveApiUrl(videoDownloadHref) ?? undefined}>Download video</a>
        ) : null}
        {scriptDownloadHref ? (
          <a href={resolveApiUrl(scriptDownloadHref) ?? undefined}>Download script</a>
        ) : null}
        {validationReportDownloadHref ? (
          <a href={resolveApiUrl(validationReportDownloadHref) ?? undefined}>
            Download validation report
          </a>
        ) : null}
      </div>
      {downloadError ? <p>{downloadError}</p> : null}
    </section>
  );
}
