import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Pin, Sparkles, TriangleAlert, CheckCircle2, X } from "lucide-react";

import type {
  WorkflowAppliedActionFeedback,
  WorkflowReviewActionCard,
  WorkflowReviewActionSection,
  WorkflowReviewControls,
  WorkflowReviewRenderContract,
  WorkflowReviewSectionId,
} from "../../lib/tasksApi";
import { useI18n } from "../../app/locale";

type TaskReviewPanelProps = {
  controls: WorkflowReviewControls;
  activeActionId: string | null;
  onRunAction: (action: WorkflowReviewActionCard) => Promise<void> | void;
};

function orderBadges(controls: WorkflowReviewControls): NonNullable<NonNullable<WorkflowReviewControls["panel_header"]>["badges"]> {
  const badges = controls.panel_header?.badges ?? [];
  const badgeOrder = controls.render_contract?.badge_order ?? [];
  if (badgeOrder.length === 0) {
    return badges;
  }

  const badgeMap = new Map(badges.map((badge) => [badge.badge_id, badge]));
  const ordered = badgeOrder.map((badgeId) => badgeMap.get(badgeId)).filter(Boolean);
  const remaining = badges.filter((badge) => !badgeOrder.includes(badge.badge_id));
  return [...ordered, ...remaining] as NonNullable<NonNullable<WorkflowReviewControls["panel_header"]>["badges"]>;
}

function orderSections(
  controls: WorkflowReviewControls
): WorkflowReviewActionSection[] {
  const sections = controls.action_sections?.items ?? [];
  const sectionOrder = controls.render_contract?.section_order ?? [];
  if (sectionOrder.length === 0) {
    return sections;
  }

  const sectionMap = new Map(sections.map((section) => [section.section_id, section]));
  const ordered = sectionOrder
    .map((sectionId) => sectionMap.get(sectionId))
    .filter(Boolean) as WorkflowReviewActionSection[];
  const remaining = sections.filter((section) => !sectionOrder.includes(section.section_id));
  return [...ordered, ...remaining];
}

function findActionById(
  sections: WorkflowReviewActionSection[],
  actionId: string | null | undefined
): WorkflowReviewActionCard | null {
  if (!actionId) {
    return null;
  }
  for (const section of sections) {
    const match = section.items.find((item) => item.action_id === actionId);
    if (match) {
      return match;
    }
  }
  return null;
}

function sectionPresentation(
  renderContract: WorkflowReviewRenderContract | null | undefined,
  sectionId: WorkflowReviewSectionId
) {
  return renderContract?.section_presentations.find((item) => item.section_id === sectionId) ?? null;
}

function toneIcon(tone: string | undefined) {
  if (tone === "ready") {
    return CheckCircle2;
  }
  if (tone === "blocked") {
    return TriangleAlert;
  }
  return Sparkles;
}

function feedbackToneClass(feedback: WorkflowAppliedActionFeedback | null | undefined): string {
  if (feedback?.tone === "success") {
    return "task-review-panel__feedback--success";
  }
  return "task-review-panel__feedback--info";
}

export function TaskReviewPanel({ controls, activeActionId, onRunAction }: TaskReviewPanelProps) {
  const { t } = useI18n();
  const header = controls.panel_header;
  const renderContract = controls.render_contract;
  const orderedBadges = useMemo(() => orderBadges(controls), [controls]);
  const orderedSections = useMemo(() => orderSections(controls), [controls]);
  const stickyAction = useMemo(
    () => findActionById(orderedSections, renderContract?.sticky_primary_action_id),
    [orderedSections, renderContract?.sticky_primary_action_id]
  );
  const [expandedSectionIds, setExpandedSectionIds] = useState<string[]>([]);
  const [feedbackDismissed, setFeedbackDismissed] = useState(false);
  const stickyActionId = renderContract?.sticky_primary_action_id ?? null;

  useEffect(() => {
    setExpandedSectionIds(renderContract?.default_expanded_section_ids ?? []);
  }, [renderContract]);

  useEffect(() => {
    setFeedbackDismissed(false);
  }, [controls.applied_action_feedback?.created_at, controls.applied_action_feedback?.memory_id]);

  if (!header || orderedSections.length === 0 || !renderContract) {
    return null;
  }

  const HeaderIcon = toneIcon(header.tone);

  return (
    <section
      className={`section-card-v2 task-review-panel task-review-panel--${renderContract.panel_tone} task-review-panel--${renderContract.display_priority}`}
      aria-label={header.title ?? "Workflow review controls"}
    >
      <div className="task-review-panel__header">
        <div className="task-review-panel__header-main">
          <div className="task-review-panel__icon-shell">
            <HeaderIcon size={18} />
          </div>
          <div className="task-review-panel__header-copy">
            <h3 className="section-title-v2 task-review-panel__title">{header.title ?? "Workflow review controls"}</h3>
            {header.summary ? <p className="task-review-panel__summary">{header.summary}</p> : null}
          </div>
        </div>
        {stickyAction ? (
          <button
            type="button"
            className={`task-review-panel__sticky-action task-review-panel__sticky-action--${renderContract.sticky_primary_action_emphasis}`}
            onClick={() => onRunAction(stickyAction)}
            disabled={stickyAction.blocked || activeActionId !== null}
            aria-busy={activeActionId === stickyAction.action_id}
          >
            <Pin size={14} />
            {activeActionId === stickyAction.action_id ? t("common.applying") : stickyAction.button_label}
          </button>
        ) : null}
      </div>

      {orderedBadges.length > 0 ? (
        <div className="task-review-panel__badges">
          {orderedBadges.map((badge) => (
            <span
              key={badge.badge_id}
              className={`task-review-panel__badge task-review-panel__badge--${badge.tone}`}
            >
              <span className="task-review-panel__badge-label">{badge.label}</span>
              <span className="task-review-panel__badge-value">{badge.value}</span>
            </span>
          ))}
        </div>
      ) : null}

      {header.highlighted_event ? (
        <div className="task-review-panel__event" role="note">
          <span className="task-review-panel__event-title">{header.highlighted_event.title}</span>
          {header.highlighted_event.summary ? (
            <span className="task-review-panel__event-summary">{header.highlighted_event.summary}</span>
          ) : null}
        </div>
      ) : null}

      <div className="task-review-panel__sections">
        {orderedSections.map((section) => {
          const presentation = sectionPresentation(renderContract, section.section_id);
          const collapsible = presentation?.collapsible ?? true;
          const expanded = expandedSectionIds.includes(section.section_id);

          return (
            <div
              key={section.section_id}
              className={`task-review-panel__section task-review-panel__section--${presentation?.tone ?? "neutral"}`}
            >
              <button
                type="button"
                className={`task-review-panel__section-header ${collapsible ? "" : "task-review-panel__section-header--static"}`}
                onClick={() => {
                  if (!collapsible) {
                    return;
                  }
                  setExpandedSectionIds((current) =>
                    current.includes(section.section_id)
                      ? current.filter((item) => item !== section.section_id)
                      : [...current, section.section_id]
                  );
                }}
                aria-expanded={expanded}
                disabled={!collapsible}
              >
                <div className="task-review-panel__section-copy">
                  <span className="task-review-panel__section-title">{section.title}</span>
                  {section.summary ? (
                    <span className="task-review-panel__section-summary">{section.summary}</span>
                  ) : null}
                </div>
                {collapsible ? (
                  expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />
                ) : null}
              </button>

              {expanded ? (
                <div className="task-review-panel__section-body">
                  {section.items.map((action) => {
                    const hideActionButton = action.action_id === stickyActionId;

                    return (
                      <div
                        key={action.action_id}
                        className={`task-review-panel__action-card ${action.blocked ? "task-review-panel__action-card--blocked" : ""}`}
                      >
                        <div className="task-review-panel__action-copy">
                          <div className="task-review-panel__action-row">
                            <span className="task-review-panel__action-title">{action.title}</span>
                            <span className={`task-review-panel__action-family task-review-panel__action-family--${action.action_family}`}>
                              {action.action_family}
                            </span>
                          </div>
                          {action.summary ? (
                            <p className="task-review-panel__action-summary">{action.summary}</p>
                          ) : null}
                          {action.reasons.length > 0 ? (
                            <div className="task-review-panel__reason-list">
                              {action.reasons.map((reason) => (
                                <span key={reason} className="task-review-panel__reason-chip">
                                  {reason}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </div>
                        {hideActionButton ? null : (
                          <button
                            type="button"
                            className={`task-review-panel__action-button ${action.is_primary ? "task-review-panel__action-button--primary" : ""}`}
                            onClick={() => onRunAction(action)}
                            disabled={action.blocked || activeActionId !== null}
                            aria-busy={activeActionId === action.action_id}
                          >
                            {activeActionId === action.action_id ? t("common.applying") : action.button_label}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {controls.applied_action_feedback && !feedbackDismissed ? (
        <div className={`task-review-panel__feedback ${feedbackToneClass(controls.applied_action_feedback)}`}>
          <div className="task-review-panel__feedback-copy">
            <span className="task-review-panel__feedback-title">{controls.applied_action_feedback.title}</span>
            {controls.applied_action_feedback.summary ? (
              <p className="task-review-panel__feedback-summary">{controls.applied_action_feedback.summary}</p>
            ) : null}
          </div>
          {renderContract.applied_feedback_dismissible ? (
            <button
              type="button"
              className="task-review-panel__feedback-dismiss"
              onClick={() => setFeedbackDismissed(true)}
              aria-label={t("common.close")}
            >
              <X size={14} />
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
