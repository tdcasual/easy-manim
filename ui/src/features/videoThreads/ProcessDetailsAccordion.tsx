import { useId, useState, type ReactNode } from "react";

import { useI18n } from "../../app/locale";
import "./VideoThreadWorkbench.css";

type ProcessDetailsAccordionProps = {
  iterationCount: number;
  participantCount: number;
  runCount: number;
  children: ReactNode;
};

export function ProcessDetailsAccordion({
  iterationCount,
  participantCount,
  runCount,
  children,
}: ProcessDetailsAccordionProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const contentId = useId();

  return (
    <section
      aria-label={t("thread.process.ariaLabel")}
      className="process-details-accordion video-thread-workbench__panel video-thread-workbench__panel--tone-neutral video-thread-workbench__panel--emphasis-supporting"
    >
      <div className="process-details-accordion__header">
        <div>
          <h2>{t("thread.process.detailsTitle")}</h2>
          <p>{t("thread.process.detailsDescription")}</p>
        </div>
        <button
          type="button"
          className="video-thread-workbench__action"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={() => setOpen((current) => !current)}
        >
          {open ? t("thread.process.hideDetails") : t("thread.process.showDetails")}
        </button>
      </div>

      <div className="video-thread-workbench__chip-list">
        <span className="video-thread-workbench__chip">{t("thread.process.iterationsLabel")}: {iterationCount}</span>
        <span className="video-thread-workbench__chip">{t("thread.process.participantsLabel")}: {participantCount}</span>
        <span className="video-thread-workbench__chip">{t("thread.process.runsLabel")}: {runCount}</span>
      </div>

      {open ? (
        <div id={contentId} className="process-details-accordion__content">
          {children}
        </div>
      ) : null}
    </section>
  );
}
