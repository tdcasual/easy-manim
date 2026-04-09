import { useMemo } from "react";

import { useI18n } from "../../app/locale";
import type { VideoThreadIterationDetail, VideoThreadSurface } from "../../lib/videoThreadsApi";
import "./VideoThreadWorkbench.css";

type VideoThreadWorkbenchProps = {
  surface: VideoThreadSurface;
  iterationDetail: VideoThreadIterationDetail | null;
  selectedIterationId: string | null;
  iterationLoading: boolean;
  showThreadHeader?: boolean;
  participantSubmitting: boolean;
  participantDraft: {
    agentId: string;
    displayName: string;
    role: string;
  };
  onSelectIteration: (iterationId: string) => void;
  onParticipantDraftChange: (field: "agentId" | "displayName" | "role", value: string) => void;
  onInviteParticipant: () => void;
  onRemoveParticipant: (participantId: string) => void;
};

export function VideoThreadWorkbench({
  surface,
  iterationDetail,
  selectedIterationId,
  iterationLoading,
  showThreadHeader = true,
  participantSubmitting,
  participantDraft,
  onSelectIteration,
  onParticipantDraftChange,
  onInviteParticipant,
  onRemoveParticipant,
}: VideoThreadWorkbenchProps) {
  const { t } = useI18n();
  const panelPresentationById = useMemo(() => {
    return new Map(
      surface.render_contract.panel_presentations.map((item) => [item.panel_id, item] as const)
    );
  }, [surface.render_contract.panel_presentations]);
  const participantManagement = surface.participants.management;
  const artifactLineage = surface.artifact_lineage ?? {
    title: t("thread.workbench.artifactLineageTitle"),
    summary: "",
    selected_result_id: null,
    items: [],
  };
  const rationaleSnapshots = surface.rationale_snapshots ?? {
    title: t("thread.workbench.rationaleSnapshotsTitle"),
    summary: "",
    current_iteration_id: null,
    items: [],
  };
  const iterationCompare = surface.iteration_compare ?? {
    title: t("thread.workbench.iterationCompareTitle"),
    summary: "",
    previous_iteration_id: null,
    current_iteration_id: null,
    previous_result_id: null,
    current_result_id: null,
    change_summary: "",
    rationale_shift_summary: "",
    continuity_status: "unknown" as const,
    continuity_summary: "",
  };
  const iterationDetailSummary = surface.iteration_detail ?? {
    title: t("thread.workbench.iterationDetailTitle"),
    summary: "",
    selected_iteration_id: null,
    resource_uri: null,
    turn_count: 0,
    run_count: 0,
    result_count: 0,
    execution_summary: {
      title: t("thread.workbench.executionSummaryTitle"),
      summary: t("thread.workbench.noIterationSelected"),
      task_id: null,
      run_id: null,
      status: "pending",
      phase: null,
      agent_id: null,
      agent_display_name: null,
      agent_role: null,
      result_id: null,
      discussion_group_id: null,
      reply_to_turn_id: null,
      latest_owner_turn_id: null,
      latest_agent_turn_id: null,
      is_active: false,
    },
  };
  const executionSummary = iterationDetail?.execution_summary ??
    iterationDetailSummary.execution_summary ?? {
      title: t("thread.workbench.executionSummaryTitle"),
      summary: t("thread.workbench.noExecutionAttached"),
      task_id: null,
      run_id: null,
      status: "pending",
      phase: null,
      agent_id: null,
      agent_display_name: null,
      agent_role: null,
      result_id: null,
      discussion_group_id: null,
      reply_to_turn_id: null,
      latest_owner_turn_id: null,
      latest_agent_turn_id: null,
      is_active: false,
    };
  const participantRuntime = surface.participant_runtime ?? {
    title: t("thread.workbench.participantRuntimeTitle"),
    summary: "",
    active_iteration_id: null,
    expected_participant_id: null,
    expected_agent_id: null,
    expected_display_name: null,
    expected_role: null,
    continuity_mode: "agent_choice" as const,
    follow_up_target_locked: false,
    recent_contributors: [],
  };

  const getPanelClassName = (panelId: string) => {
    const presentation = panelPresentationById.get(panelId);
    return [
      "video-thread-workbench__panel",
      presentation ? `video-thread-workbench__panel--tone-${presentation.tone}` : "",
      presentation ? `video-thread-workbench__panel--emphasis-${presentation.emphasis}` : "",
      presentation?.default_open ? "video-thread-workbench__panel--open" : "",
    ]
      .filter(Boolean)
      .join(" ");
  };

  return (
    <section
      className={`video-thread-workbench video-thread-workbench--${surface.render_contract.panel_tone} video-thread-workbench--${surface.render_contract.display_priority}`}
    >
      {showThreadHeader ? (
        <header className="video-thread-workbench__hero">
          <div>
            <h1 className="video-thread-workbench__title">{surface.thread_header.title}</h1>
            <p className="video-thread-workbench__summary">{surface.thread_summary}</p>
            {surface.render_contract.badge_order.length ? (
              <p className="video-thread-workbench__meta">
                {t("thread.workbench.priorityBadges")}: {surface.render_contract.badge_order.join(" / ")}
              </p>
            ) : null}
          </div>
          <div className="video-thread-workbench__status">
            {t("thread.workbench.statusLabel")}
            <strong>{surface.thread_header.status}</strong>
          </div>
        </header>
      ) : null}

      <section className={getPanelClassName("current_focus")}>
        <h2>{t("thread.workbench.focusTitle")}</h2>
        <p>{surface.current_focus.current_result_summary ?? t("thread.workbench.noSelectedResult")}</p>
        <div className="video-thread-workbench__focus-grid">
          <div>
            <span className="video-thread-workbench__label">{t("thread.workbench.currentGoal")}</span>
            <strong>
              {surface.current_focus.current_iteration_goal ?? t("thread.workbench.pendingOwner")}
            </strong>
          </div>
          <div>
            <span className="video-thread-workbench__label">{t("thread.workbench.currentAuthor")}</span>
            <strong>
              {surface.current_focus.current_result_author_display_name ??
                surface.current_focus.current_result_author_role ??
                t("thread.workbench.unassigned")}
            </strong>
          </div>
          <div>
            <span className="video-thread-workbench__label">{t("thread.workbench.ownerNextStep")}</span>
            <strong>{surface.responsibility.owner_action_required ?? t("thread.workbench.none")}</strong>
          </div>
          <div>
            <span className="video-thread-workbench__label">{t("thread.workbench.expectedRole")}</span>
            <strong>{surface.responsibility.expected_agent_role ?? t("thread.workbench.unassigned")}</strong>
          </div>
        </div>
        {surface.current_focus.current_result_selection_reason ? (
          <p>{surface.current_focus.current_result_selection_reason}</p>
        ) : null}
      </section>

      <div className="video-thread-workbench__layout">
        <section className={getPanelClassName("selection_summary")}>
          <h2>{surface.selection_summary.title}</h2>
          <p>
            {surface.selection_summary.summary || t("thread.workbench.noSelectedRationale")}
          </p>
          {surface.selection_summary.author_display_name ||
          surface.selection_summary.author_role ? (
            <div className="video-thread-workbench__turn-row">
              <strong>
                {surface.selection_summary.author_display_name ??
                  surface.selection_summary.author_role ??
                  t("thread.workbench.unknownAuthor")}
              </strong>
              <span>{surface.selection_summary.selected_result_id ?? t("thread.workbench.pendingResult")}</span>
            </div>
          ) : null}
        </section>

        <section className={getPanelClassName("latest_explanation")}>
          <h2>{surface.latest_explanation.title}</h2>
          <p>
            {surface.latest_explanation.summary || t("thread.workbench.noVisibleExplanation")}
          </p>
          {surface.latest_explanation.speaker_display_name ||
          surface.latest_explanation.speaker_role ? (
            <div className="video-thread-workbench__turn-row">
              <strong>
                {surface.latest_explanation.speaker_display_name ??
                  surface.latest_explanation.speaker_role ??
                  t("thread.discussion.agent")}
              </strong>
              <span>{surface.latest_explanation.turn_id ?? t("thread.workbench.latestExplanation")}</span>
            </div>
          ) : null}
        </section>

        <section className={getPanelClassName("decision_notes")}>
          <h2>{t("thread.workbench.decisionNotesTitle")}</h2>
          <div className="video-thread-workbench__conversation">
            {surface.decision_notes.items.length ? (
              surface.decision_notes.items.map((note) => (
                <article
                  key={note.note_id}
                  className={`video-thread-workbench__journal-entry video-thread-workbench__history-card video-thread-workbench__history-card--${note.emphasis}`}
                >
                  <div className="video-thread-workbench__turn-row">
                    <strong>{note.title}</strong>
                    <span>{note.note_kind}</span>
                  </div>
                  {note.summary ? <p>{note.summary}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {note.actor_display_name || note.actor_role ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.actorLabel")}: {note.actor_display_name ?? note.actor_role}
                      </span>
                    ) : null}
                    {note.source_iteration_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.iterationLabel")}: {note.source_iteration_id}
                      </span>
                    ) : null}
                    {note.source_turn_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.turnLabel")}: {note.source_turn_id}
                      </span>
                    ) : null}
                    {note.source_result_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.resultLabel")}: {note.source_result_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">{t("thread.workbench.noDecisionNotes")}</p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("artifact_lineage")}>
          <h2>{t("thread.workbench.artifactLineageTitle")}</h2>
          <p>{artifactLineage.summary || t("thread.workbench.noArtifactLineage")}</p>
          <div className="video-thread-workbench__conversation">
            {artifactLineage.items.length ? (
              artifactLineage.items.map((item) => (
                <article
                  key={item.lineage_id}
                  className={`video-thread-workbench__journal-entry video-thread-workbench__history-card video-thread-workbench__history-card--${item.emphasis}`}
                >
                  <div className="video-thread-workbench__turn-row">
                    <strong>
                      {item.from_result_id ?? t("thread.workbench.origin")} {"->"} {item.to_result_id ?? t("thread.workbench.pending")}
                    </strong>
                    <span>{item.status}</span>
                  </div>
                  {item.change_summary ? <p>{item.change_summary}</p> : null}
                  {item.change_reason ? <p>{item.change_reason}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {item.trigger_label ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.triggerLabel")}: {item.trigger_label}
                      </span>
                    ) : null}
                    {item.actor_display_name || item.actor_role ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.actorLabel")}: {item.actor_display_name ?? item.actor_role}
                      </span>
                    ) : null}
                    {item.iteration_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.iterationLabel")}: {item.iteration_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">{t("thread.workbench.noArtifactLineage")}</p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("rationale_snapshots")}>
          <h2>{t("thread.workbench.rationaleSnapshotsTitle")}</h2>
          <p>
            {rationaleSnapshots.summary || t("thread.workbench.noRationaleSnapshots")}
          </p>
          <div className="video-thread-workbench__conversation">
            {rationaleSnapshots.items.length ? (
              rationaleSnapshots.items.map((item) => (
                <article
                  key={item.snapshot_id}
                  className={`video-thread-workbench__journal-entry video-thread-workbench__history-card video-thread-workbench__history-card--${item.emphasis}`}
                >
                  <div className="video-thread-workbench__turn-row">
                    <strong>{item.title}</strong>
                    <span>
                      {item.snapshot_kind} / {item.status}
                    </span>
                  </div>
                  {item.summary ? <p>{item.summary}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {item.actor_display_name || item.actor_role ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.actorLabel")}: {item.actor_display_name ?? item.actor_role}
                      </span>
                    ) : null}
                    {item.iteration_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.iterationLabel")}: {item.iteration_id}
                      </span>
                    ) : null}
                    {item.source_turn_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.turnLabel")}: {item.source_turn_id}
                      </span>
                    ) : null}
                    {item.source_result_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.resultLabel")}: {item.source_result_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">{t("thread.workbench.noRationaleSnapshots")}</p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("iteration_compare")}>
          <h2>{iterationCompare.title}</h2>
          <p>{iterationCompare.summary || t("thread.workbench.noIterationComparison")}</p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.previousIteration")}</span>
              <strong>{iterationCompare.previous_iteration_id ?? t("thread.workbench.none")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.currentIteration")}</span>
              <strong>{iterationCompare.current_iteration_id ?? t("thread.workbench.none")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.previousResult")}</span>
              <strong>{iterationCompare.previous_result_id ?? t("thread.workbench.none")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.currentResult")}</span>
              <strong>{iterationCompare.current_result_id ?? t("thread.workbench.none")}</strong>
            </div>
          </div>
          {iterationCompare.change_summary ? <p>{iterationCompare.change_summary}</p> : null}
          {iterationCompare.rationale_shift_summary ? (
            <p>{iterationCompare.rationale_shift_summary}</p>
          ) : null}
          <div className="video-thread-workbench__intent-meta">
            <span className="video-thread-workbench__meta">
              {t("thread.workbench.continuityLabel")}: {iterationCompare.continuity_status}
            </span>
          </div>
          {iterationCompare.continuity_summary ? (
            <p>{iterationCompare.continuity_summary}</p>
          ) : null}
        </section>

        <section className={getPanelClassName("authorship")}>
          <h2>{t("thread.workbench.shapingTitle")}</h2>
          <p>{surface.authorship.summary || t("thread.workbench.noShapingAgent")}</p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.primaryAgent")}</span>
              <strong>
                {surface.authorship.primary_agent_display_name ??
                  surface.authorship.primary_agent_role ??
                  t("thread.workbench.unassigned")}
              </strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.roleLabel")}</span>
              <strong>{surface.authorship.primary_agent_role ?? t("thread.workbench.unassigned")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.runSource")}</span>
              <strong>{surface.authorship.source_run_id ?? t("thread.workbench.notApplicable")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.turnSource")}</span>
              <strong>{surface.authorship.source_turn_id ?? t("thread.workbench.notApplicable")}</strong>
            </div>
          </div>
        </section>

        <section className={getPanelClassName("next_recommended_move")}>
          <h2>{surface.next_recommended_move.title}</h2>
          <p>{surface.next_recommended_move.summary || t("thread.workbench.noRecommendedMove")}</p>
          <div className="video-thread-workbench__turn-row">
            <strong>
              {surface.next_recommended_move.recommended_action_label ?? t("thread.workbench.observeThread")}
            </strong>
            <span>{surface.next_recommended_move.owner_action_required ?? t("thread.workbench.none")}</span>
          </div>
        </section>

        <section className={getPanelClassName("production_journal")}>
          <h2>{t("thread.workbench.productionJournalTitle")}</h2>
          <p>
            {surface.production_journal.summary ||
              t("thread.workbench.noProductionJournal")}
          </p>
          <div className="video-thread-workbench__conversation">
            {surface.production_journal.entries.length ? (
              surface.production_journal.entries.map((entry) => (
                <article key={entry.entry_id} className="video-thread-workbench__journal-entry">
                  <div className="video-thread-workbench__turn-row">
                    <strong>{entry.title}</strong>
                    <span>
                      {entry.stage || t("thread.workbench.process")} / {entry.status || t("thread.workbench.unknown")}
                    </span>
                  </div>
                  {entry.summary ? <p>{entry.summary}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {entry.actor_display_name || entry.actor_role ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.actorLabel")}: {entry.actor_display_name ?? entry.actor_role}
                      </span>
                    ) : null}
                    {entry.task_id ? (
                      <span className="video-thread-workbench__meta">{t("thread.workbench.taskLabel")}: {entry.task_id}</span>
                    ) : null}
                    {entry.run_id ? (
                      <span className="video-thread-workbench__meta">{t("thread.workbench.runLabel")}: {entry.run_id}</span>
                    ) : null}
                    {entry.result_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.resultLabel")}: {entry.result_id}
                      </span>
                    ) : null}
                  </div>
                  {entry.resource_refs.length ? (
                    <div className="video-thread-workbench__resource-list">
                      {entry.resource_refs.map((ref) => (
                        <span key={ref} className="video-thread-workbench__meta">
                          {ref}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">{t("thread.workbench.noProductionJournal")}</p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("participant_runtime")}>
          <h2>{participantRuntime.title}</h2>
          <p>{participantRuntime.summary || t("thread.workbench.noParticipantContinuity")}</p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.expectedResponder")}</span>
              <strong>{participantRuntime.expected_display_name ?? t("thread.discussion.agentChoice")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.expectedRole")}</span>
              <strong>{participantRuntime.expected_role ?? t("thread.workbench.unassigned")}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.continuityMode")}</span>
              <strong>{participantRuntime.continuity_mode}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">{t("thread.workbench.lockedTarget")}</span>
              <strong>{participantRuntime.follow_up_target_locked ? t("thread.workbench.yes") : t("thread.workbench.no")}</strong>
            </div>
          </div>
          <div className="video-thread-workbench__intent-meta">
            <span className="video-thread-workbench__meta">
              {t("thread.workbench.continuityMode")}: {participantRuntime.continuity_mode}
            </span>
            <span className="video-thread-workbench__meta">
              {t("thread.workbench.lockedTarget")}: {participantRuntime.follow_up_target_locked ? t("thread.workbench.yes") : t("thread.workbench.no")}
            </span>
          </div>
          <div className="video-thread-workbench__conversation">
            {participantRuntime.recent_contributors.length ? (
              participantRuntime.recent_contributors.map((contributor) => (
                <article
                  key={`${contributor.participant_id ?? contributor.agent_id ?? contributor.display_name}-${contributor.contribution_kind}`}
                  className="video-thread-workbench__journal-entry"
                >
                  <div className="video-thread-workbench__turn-row">
                    <strong>{contributor.display_name}</strong>
                    <span>{contributor.contribution_kind}</span>
                  </div>
                  <p>{contributor.summary || t("thread.workbench.noRecentContribution")}</p>
                  <div className="video-thread-workbench__intent-meta">
                    {contributor.role ? (
                      <span className="video-thread-workbench__meta">{t("thread.workbench.roleLabel")}: {contributor.role}</span>
                    ) : null}
                    {contributor.agent_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.agentLabel")}: {contributor.agent_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">{t("thread.workbench.noRecentContributors")}</p>
            )}
          </div>
        </section>
      </div>

      <div className="video-thread-workbench__layout">
        <section className={getPanelClassName("history")}>
          <h2>{t("thread.workbench.historyTitle")}</h2>
          <div className="video-thread-workbench__conversation">
            {surface.history.cards.map((card) => (
              <article
                key={card.card_id}
                className={`video-thread-workbench__turn video-thread-workbench__history-card video-thread-workbench__history-card--${card.emphasis}`}
              >
                <div className="video-thread-workbench__turn-row">
                  <strong>{card.title}</strong>
                  <span>{card.actor_role ?? card.card_type}</span>
                </div>
                {card.summary ? <p>{card.summary}</p> : null}
                {card.intent_type || card.reply_to_turn_id || card.related_result_id ? (
                  <div className="video-thread-workbench__intent-meta">
                    {card.intent_type ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.intentLabel")}: {card.intent_type}
                      </span>
                    ) : null}
                    {card.reply_to_turn_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.repliesToLabel")}: {card.reply_to_turn_id}
                      </span>
                    ) : null}
                    {card.related_result_id ? (
                      <span className="video-thread-workbench__meta">
                        {t("thread.workbench.resultLabel")}: {card.related_result_id}
                      </span>
                    ) : null}
                  </div>
                ) : null}
                <div className="video-thread-workbench__turn-row">
                  <span className="video-thread-workbench__meta">
                    {card.actor_display_name ?? card.actor_role ?? t("thread.workbench.system")}
                  </span>
                  <div className="video-thread-workbench__history-meta">
                    <span className="video-thread-workbench__meta">
                      {card.iteration_id ?? t("thread.workbench.threadWide")}
                    </span>
                    <span className="video-thread-workbench__meta">{card.emphasis} {t("thread.workbench.emphasis")}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={getPanelClassName("iteration_workbench")}>
          <h2>{t("thread.workbench.iterationWorkbenchTitle")}</h2>
          <div className="video-thread-workbench__iteration-list">
            {surface.iteration_workbench.iterations.map((iteration) => (
              <article
                key={iteration.iteration_id}
                className={`video-thread-workbench__iteration ${
                  iteration.iteration_id === selectedIterationId
                    ? "video-thread-workbench__iteration--selected"
                    : ""
                }`}
              >
                <button
                  type="button"
                  className="video-thread-workbench__iteration-button"
                  onClick={() => onSelectIteration(iteration.iteration_id)}
                >
                  <div className="video-thread-workbench__iteration-row">
                    <strong>{iteration.title}</strong>
                    <span>{iteration.status}</span>
                  </div>
                  <p>{iteration.goal}</p>
                  {iteration.result_summary ? (
                    <span className="video-thread-workbench__meta">{iteration.result_summary}</span>
                  ) : null}
                </button>
              </article>
            ))}
          </div>
        </section>

        <section className={getPanelClassName("iteration_detail")}>
          <h2>{iterationDetailSummary.title}</h2>
          <p>
            {(iterationDetail?.summary ?? iterationDetailSummary.summary) ||
              t("thread.workbench.selectIterationHint")}
          </p>
          {iterationLoading ? (
            <p className="video-thread-workbench__meta">{t("thread.workbench.loadingIteration")}</p>
          ) : null}
          {iterationDetail ? (
            <div className="video-thread-workbench__conversation">
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>{iterationDetail.iteration.goal}</strong>
                  <span>{iterationDetail.iteration.status}</span>
                </div>
                <div className="video-thread-workbench__intent-meta">
                  <span className="video-thread-workbench__meta">
                    {t("thread.workbench.requestedAction")}: {iterationDetail.iteration.requested_action ?? t("thread.workbench.notApplicable")}
                  </span>
                  <span className="video-thread-workbench__meta">
                    {t("thread.workbench.focusResult")}: {iterationDetail.iteration.selected_result_id ?? t("thread.workbench.pending")}
                  </span>
                  <span className="video-thread-workbench__meta">
                    {t("thread.workbench.sourceResult")}: {iterationDetail.iteration.source_result_id ?? t("thread.workbench.origin")}
                  </span>
                </div>
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>{executionSummary.title}</strong>
                  <span>{executionSummary.phase ?? executionSummary.status}</span>
                </div>
                <p>{executionSummary.summary}</p>
                <div className="video-thread-workbench__intent-meta">
                  <span className="video-thread-workbench__meta">
                    {t("thread.discussion.agent")}:{" "}
                    {executionSummary.agent_display_name ??
                      executionSummary.agent_role ??
                      executionSummary.agent_id ??
                      "pending"}
                  </span>
                  <span className="video-thread-workbench__meta">
                    {t("thread.workbench.taskLabel")}: {executionSummary.task_id ?? t("thread.workbench.notStarted")}
                  </span>
                  <span className="video-thread-workbench__meta">
                    {t("thread.workbench.currentResultLabel")}: {executionSummary.result_id ?? t("thread.workbench.pending")}
                  </span>
                  {executionSummary.discussion_group_id ? (
                    <span className="video-thread-workbench__meta">
                      {t("thread.workbench.discussionGroupLabel")}: {executionSummary.discussion_group_id}
                    </span>
                  ) : null}
                  {executionSummary.reply_to_turn_id ? (
                    <span className="video-thread-workbench__meta">
                      {t("thread.workbench.replyTargetLabel")}: {executionSummary.reply_to_turn_id}
                    </span>
                  ) : null}
                </div>
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>{t("thread.workbench.visibleTurns")}</strong>
                  <span>{iterationDetail.turns.length}</span>
                </div>
                {iterationDetail.turns.length ? (
                  iterationDetail.turns.map((turn) => (
                    <div key={turn.turn_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{turn.title}</strong>
                        <span>
                          {turn.speaker_display_name ?? turn.speaker_role ?? turn.turn_type}
                        </span>
                      </div>
                      {turn.summary ? <p>{turn.summary}</p> : null}
                      {turn.addressed_display_name || turn.addressed_participant_id ? (
                        <div className="video-thread-workbench__intent-meta">
                          <span className="video-thread-workbench__meta">
                            {t("thread.workbench.addressedTo")}:{" "}
                            {turn.addressed_display_name ?? turn.addressed_participant_id}
                          </span>
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p className="video-thread-workbench__meta">{t("thread.workbench.noTurns")}</p>
                )}
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>{t("thread.workbench.agentRuns")}</strong>
                  <span>{iterationDetail.runs.length}</span>
                </div>
                {iterationDetail.runs.length ? (
                  iterationDetail.runs.map((run) => (
                    <div key={run.run_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{run.agent_display_name ?? run.role}</strong>
                        <span>{run.phase ?? run.status}</span>
                      </div>
                      {run.output_summary ? <p>{run.output_summary}</p> : null}
                    </div>
                  ))
                ) : (
                  <p className="video-thread-workbench__meta">{t("thread.workbench.noRuns")}</p>
                )}
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>{t("thread.workbench.producedResults")}</strong>
                  <span>{iterationDetail.results.length}</span>
                </div>
                {iterationDetail.results.length ? (
                  iterationDetail.results.map((result) => (
                    <div key={result.result_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{result.result_id}</strong>
                        <span>{result.selected ? t("thread.timeline.currentVersion") : result.status}</span>
                      </div>
                      {result.result_summary ? <p>{result.result_summary}</p> : null}
                    </div>
                  ))
                ) : (
                  <p className="video-thread-workbench__meta">{t("thread.workbench.noResults")}</p>
                )}
              </article>
            </div>
          ) : (
            <div className="video-thread-workbench__intent-meta">
              <span className="video-thread-workbench__meta">
                {t("thread.workbench.visibleTurns")}: {iterationDetailSummary.turn_count}
              </span>
              <span className="video-thread-workbench__meta">
                {t("thread.workbench.agentRuns")}: {iterationDetailSummary.run_count}
              </span>
              <span className="video-thread-workbench__meta">
                {t("thread.workbench.producedResults")}: {iterationDetailSummary.result_count}
              </span>
            </div>
          )}
        </section>
      </div>

      <section className={getPanelClassName("process")}>
        <h2>{t("thread.workbench.processTitle")}</h2>
        <div className="video-thread-workbench__process">
          {surface.process.runs.map((run) => (
            <article key={run.run_id} className="video-thread-workbench__run">
              <div className="video-thread-workbench__turn-row">
                <strong>{run.role}</strong>
                <span>{run.phase ?? run.status}</span>
              </div>
              {run.output_summary ? <p>{run.output_summary}</p> : null}
            </article>
          ))}
        </div>
      </section>

      <section className={getPanelClassName("participants")}>
        <h2>{t("thread.workbench.participantsTitle")}</h2>
        <div className="video-thread-workbench__conversation">
          {surface.participants.items.map((participant) => (
            <article key={participant.participant_id} className="video-thread-workbench__turn">
              <div className="video-thread-workbench__turn-row">
                <strong>{participant.display_name}</strong>
                <span>{participant.role}</span>
              </div>
              {participant.agent_id ? <p>{participant.agent_id}</p> : null}
              {participantManagement.can_remove &&
              participantManagement.removable_participant_ids.includes(
                participant.participant_id
              ) ? (
                <button
                  type="button"
                  className="video-thread-workbench__inline-button"
                  onClick={() => onRemoveParticipant(participant.participant_id)}
                  disabled={participantSubmitting}
                  aria-label={`${participantManagement.remove_label} ${participant.display_name}`}
                >
                  {participantManagement.remove_label}
                </button>
              ) : null}
            </article>
          ))}
        </div>
        <div className="video-thread-workbench__participant-management">
          <div className="video-thread-workbench__turn-row">
            <strong>{t("thread.workbench.ownerControls")}</strong>
            <span>{participantManagement.can_manage ? t("thread.workbench.active") : t("thread.workbench.viewOnly")}</span>
          </div>
          <p>{participantManagement.context_hint || participantManagement.disabled_reason}</p>
          <div className="video-thread-workbench__participant-form">
            <label className="video-thread-workbench__label" htmlFor="participant-agent-id">
              {t("thread.workbench.participantAgentIdLabel")}
            </label>
            <input
              id="participant-agent-id"
              className="video-thread-workbench__input"
              value={participantDraft.agentId}
              placeholder={participantManagement.invite_placeholder}
              onChange={(event) => onParticipantDraftChange("agentId", event.target.value)}
              disabled={participantSubmitting || !participantManagement.can_invite}
            />
            <label className="video-thread-workbench__label" htmlFor="participant-display-name">
              {t("thread.workbench.participantDisplayNameLabel")}
            </label>
            <input
              id="participant-display-name"
              className="video-thread-workbench__input"
              value={participantDraft.displayName}
              placeholder={t("thread.workbench.rolePlaceholder")}
              onChange={(event) => onParticipantDraftChange("displayName", event.target.value)}
              disabled={participantSubmitting || !participantManagement.can_invite}
            />
            <label className="video-thread-workbench__label" htmlFor="participant-role">
              {t("thread.workbench.participantRoleLabel")}
            </label>
            <input
              id="participant-role"
              className="video-thread-workbench__input"
              value={participantDraft.role}
              placeholder={participantManagement.default_role}
              onChange={(event) => onParticipantDraftChange("role", event.target.value)}
              disabled={participantSubmitting || !participantManagement.can_invite}
            />
          </div>
          <div className="video-thread-workbench__actions">
            <button
              type="button"
              className="video-thread-workbench__action"
              disabled={
                participantSubmitting ||
                !participantManagement.can_invite ||
                !participantDraft.agentId.trim()
              }
              onClick={onInviteParticipant}
            >
              {participantManagement.invite_label}
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}
