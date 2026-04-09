import { type TaskResult } from "../../lib/tasksApi";
import { resolveApiUrl, ARTIFACT_PATHS } from "../../lib/api";
import { useI18n } from "../../app/locale";
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
  const { t } = useI18n();
  const videoDownloadHref =
    downloads?.video_download_url ?? (selectedTaskId ? ARTIFACT_PATHS.video(selectedTaskId) : null);
  const scriptDownloadHref =
    downloads?.script_download_url ??
    (selectedTaskId ? ARTIFACT_PATHS.script(selectedTaskId) : null);
  const validationReportDownloadHref =
    downloads?.validation_report_download_url ??
    (selectedTaskId ? ARTIFACT_PATHS.validationReport(selectedTaskId) : null);
  const summary =
    selectedResult?.result_summary ??
    surface.current_focus.current_result_summary ??
    t("thread.hero.noSelectedVersion");

  return (
    <section aria-label={t("thread.hero.ariaLabel")}>
      <h2>{t("thread.hero.title")}</h2>
      <p>{summary}</p>
      <p>
        {t("thread.hero.selectedResultLabel")}:{" "}
        {selectedResult?.result_id ?? surface.current_focus.current_result_id ?? t("thread.workbench.none")}
      </p>
      <p>
        {t("thread.hero.selectedIterationLabel")}:{" "}
        {selectedIterationId ?? surface.current_focus.current_iteration_id ?? t("thread.workbench.none")}
      </p>
      {selectedTaskId ? <p>{t("thread.hero.sourceTaskLabel")}: {selectedTaskId}</p> : null}
      <div>
        {videoDownloadHref ? (
          <a href={resolveApiUrl(videoDownloadHref) ?? undefined}>{t("thread.hero.downloadVideo")}</a>
        ) : null}
        {scriptDownloadHref ? (
          <a href={resolveApiUrl(scriptDownloadHref) ?? undefined}>{t("thread.hero.downloadScript")}</a>
        ) : null}
        {validationReportDownloadHref ? (
          <a href={resolveApiUrl(validationReportDownloadHref) ?? undefined}>
            {t("thread.hero.downloadValidationReport")}
          </a>
        ) : null}
      </div>
      {downloadError ? <p>{downloadError}</p> : null}
    </section>
  );
}
