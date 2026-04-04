import { useId, useState, type ReactNode } from "react";

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
  const [open, setOpen] = useState(false);
  const contentId = useId();

  return (
    <section
      aria-label="Process details"
      className="process-details-accordion video-thread-workbench__panel video-thread-workbench__panel--tone-neutral video-thread-workbench__panel--emphasis-supporting"
    >
      <div className="process-details-accordion__header">
        <div>
          <h2>Process details</h2>
          <p>Open the operator view for iteration history, participant controls, and agent execution detail.</p>
        </div>
        <button
          type="button"
          className="video-thread-workbench__action"
          aria-expanded={open}
          aria-controls={contentId}
          onClick={() => setOpen((current) => !current)}
        >
          {open ? "Hide process details" : "Show process details"}
        </button>
      </div>

      <div className="video-thread-workbench__chip-list">
        <span className="video-thread-workbench__chip">Iterations: {iterationCount}</span>
        <span className="video-thread-workbench__chip">Participants: {participantCount}</span>
        <span className="video-thread-workbench__chip">Runs: {runCount}</span>
      </div>

      {open ? (
        <div id={contentId} className="process-details-accordion__content">
          {children}
        </div>
      ) : null}
    </section>
  );
}
