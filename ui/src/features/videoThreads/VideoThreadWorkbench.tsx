import { useMemo } from "react";

import type {
  VideoThreadAction,
  VideoThreadIterationDetail,
  VideoThreadSurface,
} from "../../lib/videoThreadsApi";
import "./VideoThreadWorkbench.css";

type VideoThreadWorkbenchProps = {
  surface: VideoThreadSurface;
  iterationDetail: VideoThreadIterationDetail | null;
  selectedIterationId: string | null;
  iterationLoading: boolean;
  draft: string;
  activeActionId: string | null;
  submitting: boolean;
  participantSubmitting: boolean;
  participantDraft: {
    agentId: string;
    displayName: string;
    role: string;
  };
  onDraftChange: (value: string) => void;
  onSelectIteration: (iterationId: string) => void;
  onSelectAction: (actionId: string) => void;
  onSubmit: () => void;
  onParticipantDraftChange: (field: "agentId" | "displayName" | "role", value: string) => void;
  onInviteParticipant: () => void;
  onRemoveParticipant: (participantId: string) => void;
};

export function VideoThreadWorkbench({
  surface,
  iterationDetail,
  selectedIterationId,
  iterationLoading,
  draft,
  activeActionId,
  submitting,
  participantSubmitting,
  participantDraft,
  onDraftChange,
  onSelectIteration,
  onSelectAction,
  onSubmit,
  onParticipantDraftChange,
  onInviteParticipant,
  onRemoveParticipant,
}: VideoThreadWorkbenchProps) {
  const selectedAction = useMemo<VideoThreadAction | null>(() => {
    return (
      surface.actions.items.find((item) => item.action_id === activeActionId) ??
      surface.actions.items[0] ??
      null
    );
  }, [activeActionId, surface.actions.items]);
  const panelPresentationById = useMemo(() => {
    return new Map(
      surface.render_contract.panel_presentations.map((item) => [item.panel_id, item] as const)
    );
  }, [surface.render_contract.panel_presentations]);
  const participantManagement = surface.participants.management;
  const expandedPanelsLabel = surface.render_contract.default_expanded_panels.join(", ") || "none";
  const artifactLineage = surface.artifact_lineage ?? {
    title: "Artifact Lineage",
    summary: "",
    selected_result_id: null,
    items: [],
  };
  const rationaleSnapshots = surface.rationale_snapshots ?? {
    title: "Rationale Snapshots",
    summary: "",
    current_iteration_id: null,
    items: [],
  };
  const iterationCompare = surface.iteration_compare ?? {
    title: "Iteration Compare",
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
    title: "Iteration Detail",
    summary: "",
    selected_iteration_id: null,
    resource_uri: null,
    turn_count: 0,
    run_count: 0,
    result_count: 0,
    execution_summary: {
      title: "Execution Summary",
      summary: "No iteration is selected yet.",
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
      title: "Execution Summary",
      summary: "No tracked execution is attached to this iteration yet.",
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
  const activeComposerTarget = iterationDetail?.composer_target ??
    surface.composer.target ?? {
      iteration_id: null,
      result_id: null,
      addressed_participant_id: null,
      addressed_agent_id: null,
      addressed_display_name: null,
      agent_role: null,
      agent_display_name: null,
      summary: "",
    };
  const discussionRuntime = surface.discussion_runtime ?? {
    title: "Discussion Runtime",
    summary: "",
    active_iteration_id: null,
    active_discussion_group_id: null,
    continuity_scope: "thread" as const,
    reply_policy: "continue_thread" as const,
    default_intent_type: null,
    default_reply_to_turn_id: null,
    default_related_result_id: null,
    addressed_participant_id: null,
    addressed_agent_id: null,
    addressed_display_name: null,
    suggested_follow_up_modes: [],
    active_thread_title: null,
    active_thread_summary: "",
    latest_owner_turn_id: null,
    latest_agent_turn_id: null,
    latest_agent_summary: "",
  };
  const participantRuntime = surface.participant_runtime ?? {
    title: "Participant Runtime",
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
  const replyPolicyHint =
    discussionRuntime.reply_policy === "continue_thread"
      ? "Stay inside the active discussion thread for the next owner follow-up."
      : discussionRuntime.reply_policy === "start_new_thread"
        ? "Start a new discussion thread for the next owner follow-up."
        : "The responding agent may decide whether to continue or branch the discussion.";

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
      <header className="video-thread-workbench__hero">
        <div>
          <h1 className="video-thread-workbench__title">{surface.thread_header.title}</h1>
          <p className="video-thread-workbench__summary">{surface.thread_summary}</p>
          {surface.render_contract.badge_order.length ? (
            <p className="video-thread-workbench__meta">
              Priority badges: {surface.render_contract.badge_order.join(" / ")}
            </p>
          ) : null}
        </div>
        <div className="video-thread-workbench__status">
          <span>Status</span>
          <strong>{surface.thread_header.status}</strong>
        </div>
      </header>

      <section className={getPanelClassName("current_focus")}>
        <h2>Selected result with current focus</h2>
        <p>{surface.current_focus.current_result_summary || "No selected result yet."}</p>
        <div className="video-thread-workbench__focus-grid">
          <div>
            <span className="video-thread-workbench__label">Current goal</span>
            <strong>{surface.current_focus.current_iteration_goal || "Pending owner direction"}</strong>
          </div>
          <div>
            <span className="video-thread-workbench__label">Current author</span>
            <strong>
              {surface.current_focus.current_result_author_display_name ||
                surface.current_focus.current_result_author_role ||
                "unassigned"}
            </strong>
          </div>
          <div>
            <span className="video-thread-workbench__label">Owner next step</span>
            <strong>{surface.responsibility.owner_action_required || "none"}</strong>
          </div>
          <div>
            <span className="video-thread-workbench__label">Expected agent role</span>
            <strong>{surface.responsibility.expected_agent_role || "unassigned"}</strong>
          </div>
        </div>
        {surface.current_focus.current_result_selection_reason ? (
          <p>{surface.current_focus.current_result_selection_reason}</p>
        ) : null}
      </section>

      <div className="video-thread-workbench__layout">
        <section className={getPanelClassName("selection_summary")}>
          <h2>{surface.selection_summary.title}</h2>
          <p>{surface.selection_summary.summary || "No selected-result rationale is available yet."}</p>
          {surface.selection_summary.author_display_name || surface.selection_summary.author_role ? (
            <div className="video-thread-workbench__turn-row">
              <strong>
                {surface.selection_summary.author_display_name ||
                  surface.selection_summary.author_role ||
                  "Unknown author"}
              </strong>
              <span>{surface.selection_summary.selected_result_id || "pending result"}</span>
            </div>
          ) : null}
        </section>

        <section className={getPanelClassName("latest_explanation")}>
          <h2>{surface.latest_explanation.title}</h2>
          <p>{surface.latest_explanation.summary || "No visible explanation has been recorded yet."}</p>
          {surface.latest_explanation.speaker_display_name || surface.latest_explanation.speaker_role ? (
            <div className="video-thread-workbench__turn-row">
              <strong>
                {surface.latest_explanation.speaker_display_name ||
                  surface.latest_explanation.speaker_role ||
                  "Agent"}
              </strong>
              <span>{surface.latest_explanation.turn_id || "latest explanation"}</span>
            </div>
          ) : null}
        </section>

        <section className={getPanelClassName("decision_notes")}>
          <h2>Decision Notes</h2>
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
                        Actor: {note.actor_display_name || note.actor_role}
                      </span>
                    ) : null}
                    {note.source_iteration_id ? (
                      <span className="video-thread-workbench__meta">
                        Iteration: {note.source_iteration_id}
                      </span>
                    ) : null}
                    {note.source_turn_id ? (
                      <span className="video-thread-workbench__meta">Turn: {note.source_turn_id}</span>
                    ) : null}
                    {note.source_result_id ? (
                      <span className="video-thread-workbench__meta">
                        Result: {note.source_result_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">
                No decision notes are available yet.
              </p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("artifact_lineage")}>
          <h2>Artifact Lineage</h2>
          <p>
            {artifactLineage.summary || "No visible artifact lineage is available yet."}
          </p>
          <div className="video-thread-workbench__conversation">
            {artifactLineage.items.length ? (
              artifactLineage.items.map((item) => (
                <article
                  key={item.lineage_id}
                  className={`video-thread-workbench__journal-entry video-thread-workbench__history-card video-thread-workbench__history-card--${item.emphasis}`}
                >
                  <div className="video-thread-workbench__turn-row">
                    <strong>
                      {(item.from_result_id || "origin")} {"->"} {item.to_result_id || "pending"}
                    </strong>
                    <span>{item.status}</span>
                  </div>
                  {item.change_summary ? <p>{item.change_summary}</p> : null}
                  {item.change_reason ? <p>{item.change_reason}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {item.trigger_label ? (
                      <span className="video-thread-workbench__meta">
                        Trigger: {item.trigger_label}
                      </span>
                    ) : null}
                    {item.actor_display_name || item.actor_role ? (
                      <span className="video-thread-workbench__meta">
                        Actor: {item.actor_display_name || item.actor_role}
                      </span>
                    ) : null}
                    {item.iteration_id ? (
                      <span className="video-thread-workbench__meta">
                        Iteration: {item.iteration_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">
                No visible artifact lineage is available yet.
              </p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("rationale_snapshots")}>
          <h2>Rationale Snapshots</h2>
          <p>
            {rationaleSnapshots.summary || "No canonical rationale snapshots are available yet."}
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
                        Actor: {item.actor_display_name || item.actor_role}
                      </span>
                    ) : null}
                    {item.iteration_id ? (
                      <span className="video-thread-workbench__meta">
                        Iteration: {item.iteration_id}
                      </span>
                    ) : null}
                    {item.source_turn_id ? (
                      <span className="video-thread-workbench__meta">
                        Turn: {item.source_turn_id}
                      </span>
                    ) : null}
                    {item.source_result_id ? (
                      <span className="video-thread-workbench__meta">
                        Result: {item.source_result_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">
                No canonical rationale snapshots are available yet.
              </p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("iteration_compare")}>
          <h2>{iterationCompare.title}</h2>
          <p>
            {iterationCompare.summary || "No stable iteration comparison is available yet."}
          </p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">Previous iteration</span>
              <strong>{iterationCompare.previous_iteration_id || "none"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Current iteration</span>
              <strong>{iterationCompare.current_iteration_id || "none"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Previous result</span>
              <strong>{iterationCompare.previous_result_id || "none"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Current result</span>
              <strong>{iterationCompare.current_result_id || "none"}</strong>
            </div>
          </div>
          {iterationCompare.change_summary ? <p>{iterationCompare.change_summary}</p> : null}
          {iterationCompare.rationale_shift_summary ? (
            <p>{iterationCompare.rationale_shift_summary}</p>
          ) : null}
          <div className="video-thread-workbench__intent-meta">
            <span className="video-thread-workbench__meta">
              Continuity: {iterationCompare.continuity_status}
            </span>
          </div>
          {iterationCompare.continuity_summary ? <p>{iterationCompare.continuity_summary}</p> : null}
        </section>

        <section className={getPanelClassName("authorship")}>
          <h2>Who Shaped This Version</h2>
          <p>{surface.authorship.summary || "No shaping agent has been projected yet."}</p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">Primary agent</span>
              <strong>
                {surface.authorship.primary_agent_display_name ||
                  surface.authorship.primary_agent_role ||
                  "unassigned"}
              </strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Role</span>
              <strong>{surface.authorship.primary_agent_role || "unassigned"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Run source</span>
              <strong>{surface.authorship.source_run_id || "n/a"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Turn source</span>
              <strong>{surface.authorship.source_turn_id || "n/a"}</strong>
            </div>
          </div>
        </section>

        <section className={getPanelClassName("next_recommended_move")}>
          <h2>{surface.next_recommended_move.title}</h2>
          <p>{surface.next_recommended_move.summary || "No recommended move is available yet."}</p>
          <div className="video-thread-workbench__turn-row">
            <strong>{surface.next_recommended_move.recommended_action_label || "Observe thread"}</strong>
            <span>{surface.next_recommended_move.owner_action_required || "none"}</span>
          </div>
        </section>

        <section className={getPanelClassName("production_journal")}>
          <h2>Production Journal</h2>
          <p>
            {surface.production_journal.summary || "No visible production entries are available yet."}
          </p>
          <div className="video-thread-workbench__conversation">
            {surface.production_journal.entries.length ? (
              surface.production_journal.entries.map((entry) => (
                <article key={entry.entry_id} className="video-thread-workbench__journal-entry">
                  <div className="video-thread-workbench__turn-row">
                    <strong>{entry.title}</strong>
                    <span>
                      {entry.stage || "process"} / {entry.status || "unknown"}
                    </span>
                  </div>
                  {entry.summary ? <p>{entry.summary}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {entry.actor_display_name || entry.actor_role ? (
                      <span className="video-thread-workbench__meta">
                        Actor: {entry.actor_display_name || entry.actor_role}
                      </span>
                    ) : null}
                    {entry.task_id ? (
                      <span className="video-thread-workbench__meta">Task: {entry.task_id}</span>
                    ) : null}
                    {entry.run_id ? (
                      <span className="video-thread-workbench__meta">Run: {entry.run_id}</span>
                    ) : null}
                    {entry.result_id ? (
                      <span className="video-thread-workbench__meta">Result: {entry.result_id}</span>
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
              <p className="video-thread-workbench__meta">
                No production journal entries have been projected yet.
              </p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("discussion_runtime")}>
          <h2>{discussionRuntime.title}</h2>
          <p>{discussionRuntime.summary || "No active discussion runtime has been projected yet."}</p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">Active thread</span>
              <strong>{discussionRuntime.active_thread_title || "No active thread yet"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Reply target</span>
              <strong>{discussionRuntime.addressed_display_name || "Agent choice"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Continuity</span>
              <strong>{discussionRuntime.continuity_scope}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Reply policy</span>
              <strong>{discussionRuntime.reply_policy}</strong>
            </div>
          </div>
          {discussionRuntime.active_thread_summary ? (
            <p>{discussionRuntime.active_thread_summary}</p>
          ) : null}
          <div className="video-thread-workbench__intent-meta">
            <span className="video-thread-workbench__meta">
              Continuity: {discussionRuntime.continuity_scope}
            </span>
            <span className="video-thread-workbench__meta">
              Reply policy: {discussionRuntime.reply_policy}
            </span>
            {discussionRuntime.default_reply_to_turn_id ? (
              <span className="video-thread-workbench__meta">
                Reply to: {discussionRuntime.default_reply_to_turn_id}
              </span>
            ) : null}
            {discussionRuntime.default_related_result_id ? (
              <span className="video-thread-workbench__meta">
                Result: {discussionRuntime.default_related_result_id}
              </span>
            ) : null}
          </div>
          <p className="video-thread-workbench__meta">{replyPolicyHint}</p>
          {discussionRuntime.suggested_follow_up_modes.length ? (
            <div className="video-thread-workbench__chip-list">
              {discussionRuntime.suggested_follow_up_modes.map((mode) => (
                <span key={mode} className="video-thread-workbench__chip">
                  Suggested: {mode}
                </span>
              ))}
            </div>
          ) : null}
          <div className="video-thread-workbench__conversation">
            <article className="video-thread-workbench__journal-entry">
              <div className="video-thread-workbench__turn-row">
                <strong>Latest owner prompt</strong>
                <span>{discussionRuntime.latest_owner_turn_id || "waiting"}</span>
              </div>
              <p>{discussionRuntime.active_thread_summary || "No active owner prompt summary is available yet."}</p>
            </article>
            <article className="video-thread-workbench__journal-entry">
              <div className="video-thread-workbench__turn-row">
                <strong>Latest agent answer</strong>
                <span>{discussionRuntime.latest_agent_turn_id || "awaiting reply"}</span>
              </div>
              <p>{discussionRuntime.latest_agent_summary || "No visible agent answer has been projected yet."}</p>
            </article>
          </div>
        </section>

        <section className={getPanelClassName("participant_runtime")}>
          <h2>{participantRuntime.title}</h2>
          <p>{participantRuntime.summary || "No participant continuity has been projected yet."}</p>
          <div className="video-thread-workbench__focus-grid">
            <div>
              <span className="video-thread-workbench__label">Expected responder</span>
              <strong>{participantRuntime.expected_display_name || "Agent choice"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Expected role</span>
              <strong>{participantRuntime.expected_role || "unassigned"}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Continuity mode</span>
              <strong>{participantRuntime.continuity_mode}</strong>
            </div>
            <div>
              <span className="video-thread-workbench__label">Locked target</span>
              <strong>{participantRuntime.follow_up_target_locked ? "yes" : "no"}</strong>
            </div>
          </div>
          <div className="video-thread-workbench__intent-meta">
            <span className="video-thread-workbench__meta">
              Continuity mode: {participantRuntime.continuity_mode}
            </span>
            <span className="video-thread-workbench__meta">
              Locked target: {participantRuntime.follow_up_target_locked ? "yes" : "no"}
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
                  <p>{contributor.summary || "No recent contribution summary is available yet."}</p>
                  <div className="video-thread-workbench__intent-meta">
                    {contributor.role ? (
                      <span className="video-thread-workbench__meta">
                        Role: {contributor.role}
                      </span>
                    ) : null}
                    {contributor.agent_id ? (
                      <span className="video-thread-workbench__meta">
                        Agent: {contributor.agent_id}
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">
                No recent contributors are available yet.
              </p>
            )}
          </div>
        </section>

        <section className={getPanelClassName("discussion_groups")}>
          <h2>Discussion Threads</h2>
          <div className="video-thread-workbench__conversation">
            {surface.discussion_groups.groups.length ? (
              surface.discussion_groups.groups.map((group) => (
                <article key={group.group_id} className="video-thread-workbench__discussion-group">
                  <div className="video-thread-workbench__turn-row">
                    <strong>{group.prompt_title}</strong>
                    <span>{group.status}</span>
                  </div>
                  {group.prompt_summary ? <p>{group.prompt_summary}</p> : null}
                  <div className="video-thread-workbench__intent-meta">
                    {group.prompt_intent_type ? (
                      <span className="video-thread-workbench__meta">
                        Intent: {group.prompt_intent_type}
                      </span>
                    ) : null}
                    {group.related_result_id ? (
                      <span className="video-thread-workbench__meta">
                        Result: {group.related_result_id}
                      </span>
                    ) : null}
                  </div>
                  <div className="video-thread-workbench__turn-row">
                    <span className="video-thread-workbench__meta">
                      {group.prompt_actor_display_name || group.prompt_actor_role || "Owner"}
                    </span>
                    <span className="video-thread-workbench__meta">
                      {group.iteration_id || group.prompt_turn_id}
                    </span>
                  </div>
                  {group.replies.length ? (
                    <div className="video-thread-workbench__reply-list">
                      {group.replies.map((reply) => (
                        <article key={reply.turn_id} className="video-thread-workbench__reply">
                          <div className="video-thread-workbench__turn-row">
                            <strong>{reply.title}</strong>
                            <span>{reply.speaker_role || "agent"}</span>
                          </div>
                          {reply.summary ? <p>{reply.summary}</p> : null}
                          <div className="video-thread-workbench__intent-meta">
                            {reply.intent_type ? (
                              <span className="video-thread-workbench__meta">
                                Intent: {reply.intent_type}
                              </span>
                            ) : null}
                            {reply.related_result_id ? (
                              <span className="video-thread-workbench__meta">
                                Result: {reply.related_result_id}
                              </span>
                            ) : null}
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="video-thread-workbench__meta">
                      No reply has been attached to this discussion yet.
                    </p>
                  )}
                </article>
              ))
            ) : (
              <p className="video-thread-workbench__meta">
                No grouped discussion threads are available yet.
              </p>
            )}
          </div>
        </section>
      </div>

      <div className="video-thread-workbench__layout">
        <section className={getPanelClassName("history")}>
          <h2>How This Video Got Here</h2>
          <div className="video-thread-workbench__conversation">
            {surface.history.cards.map((card) => (
              <article
                key={card.card_id}
                className={`video-thread-workbench__turn video-thread-workbench__history-card video-thread-workbench__history-card--${card.emphasis}`}
              >
                <div className="video-thread-workbench__turn-row">
                  <strong>{card.title}</strong>
                  <span>{card.actor_role || card.card_type}</span>
                </div>
                {card.summary ? <p>{card.summary}</p> : null}
                {card.intent_type || card.reply_to_turn_id || card.related_result_id ? (
                  <div className="video-thread-workbench__intent-meta">
                    {card.intent_type ? (
                      <span className="video-thread-workbench__meta">Intent: {card.intent_type}</span>
                    ) : null}
                    {card.reply_to_turn_id ? (
                      <span className="video-thread-workbench__meta">
                        Replies to: {card.reply_to_turn_id}
                      </span>
                    ) : null}
                    {card.related_result_id ? (
                      <span className="video-thread-workbench__meta">
                        Result: {card.related_result_id}
                      </span>
                    ) : null}
                  </div>
                ) : null}
                <div className="video-thread-workbench__turn-row">
                  <span className="video-thread-workbench__meta">
                    {card.actor_display_name || card.actor_role || "System"}
                  </span>
                  <div className="video-thread-workbench__history-meta">
                    <span className="video-thread-workbench__meta">{card.iteration_id || "thread-wide"}</span>
                    <span className="video-thread-workbench__meta">{card.emphasis} emphasis</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className={getPanelClassName("iteration_workbench")}>
          <h2>Iteration workbench</h2>
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
            {iterationDetail?.summary ||
              iterationDetailSummary.summary ||
              "Select an iteration to inspect its visible process and discussion."}
          </p>
          {iterationLoading ? (
            <p className="video-thread-workbench__meta">Loading iteration detail...</p>
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
                    Requested action: {iterationDetail.iteration.requested_action || "n/a"}
                  </span>
                  <span className="video-thread-workbench__meta">
                    Focus result: {iterationDetail.iteration.selected_result_id || "pending"}
                  </span>
                  <span className="video-thread-workbench__meta">
                    Source result: {iterationDetail.iteration.source_result_id || "origin"}
                  </span>
                </div>
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>{executionSummary.title}</strong>
                  <span>{executionSummary.phase || executionSummary.status}</span>
                </div>
                <p>{executionSummary.summary}</p>
                <div className="video-thread-workbench__intent-meta">
                  <span className="video-thread-workbench__meta">
                    Agent:{" "}
                    {executionSummary.agent_display_name ||
                      executionSummary.agent_role ||
                      executionSummary.agent_id ||
                      "pending"}
                  </span>
                  <span className="video-thread-workbench__meta">
                    Task: {executionSummary.task_id || "not started"}
                  </span>
                  <span className="video-thread-workbench__meta">
                    Current result: {executionSummary.result_id || "pending"}
                  </span>
                  {executionSummary.discussion_group_id ? (
                    <span className="video-thread-workbench__meta">
                      Discussion group: {executionSummary.discussion_group_id}
                    </span>
                  ) : null}
                  {executionSummary.reply_to_turn_id ? (
                    <span className="video-thread-workbench__meta">
                      Reply target: {executionSummary.reply_to_turn_id}
                    </span>
                  ) : null}
                </div>
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>Visible turns</strong>
                  <span>{iterationDetail.turns.length}</span>
                </div>
                {iterationDetail.turns.length ? (
                  iterationDetail.turns.map((turn) => (
                    <div key={turn.turn_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{turn.title}</strong>
                        <span>{turn.speaker_display_name || turn.speaker_role || turn.turn_type}</span>
                      </div>
                      {turn.summary ? <p>{turn.summary}</p> : null}
                      {turn.addressed_display_name || turn.addressed_participant_id ? (
                        <div className="video-thread-workbench__intent-meta">
                          <span className="video-thread-workbench__meta">
                            Addressed to: {turn.addressed_display_name || turn.addressed_participant_id}
                          </span>
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p className="video-thread-workbench__meta">No visible turns are attached yet.</p>
                )}
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>Agent runs</strong>
                  <span>{iterationDetail.runs.length}</span>
                </div>
                {iterationDetail.runs.length ? (
                  iterationDetail.runs.map((run) => (
                    <div key={run.run_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{run.agent_display_name || run.role}</strong>
                        <span>{run.phase || run.status}</span>
                      </div>
                      {run.output_summary ? <p>{run.output_summary}</p> : null}
                    </div>
                  ))
                ) : (
                  <p className="video-thread-workbench__meta">No agent runs are attached yet.</p>
                )}
              </article>
              <article className="video-thread-workbench__journal-entry">
                <div className="video-thread-workbench__turn-row">
                  <strong>Produced results</strong>
                  <span>{iterationDetail.results.length}</span>
                </div>
                {iterationDetail.results.length ? (
                  iterationDetail.results.map((result) => (
                    <div key={result.result_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{result.result_id}</strong>
                        <span>{result.selected ? "selected" : result.status}</span>
                      </div>
                      {result.result_summary ? <p>{result.result_summary}</p> : null}
                    </div>
                  ))
                ) : (
                  <p className="video-thread-workbench__meta">No results are attached yet.</p>
                )}
              </article>
            </div>
          ) : (
            <div className="video-thread-workbench__intent-meta">
              <span className="video-thread-workbench__meta">Turns: {iterationDetailSummary.turn_count}</span>
              <span className="video-thread-workbench__meta">Runs: {iterationDetailSummary.run_count}</span>
              <span className="video-thread-workbench__meta">Results: {iterationDetailSummary.result_count}</span>
            </div>
          )}
        </section>

        <section className={getPanelClassName("conversation")}>
          <h2>Conversation</h2>
          <div className="video-thread-workbench__conversation">
            {surface.conversation.turns.map((turn) => (
              <article key={turn.turn_id} className="video-thread-workbench__turn">
                <div className="video-thread-workbench__turn-row">
                  <strong>{turn.title}</strong>
                  <span>{turn.speaker_role || turn.speaker_type}</span>
                </div>
                {turn.summary ? <p>{turn.summary}</p> : null}
                {turn.intent_type || turn.reply_to_turn_id || turn.related_result_id ? (
                  <div className="video-thread-workbench__intent-meta">
                    {turn.intent_type ? (
                      <span className="video-thread-workbench__meta">Intent: {turn.intent_type}</span>
                    ) : null}
                    {turn.reply_to_turn_id ? (
                      <span className="video-thread-workbench__meta">
                        Replies to: {turn.reply_to_turn_id}
                      </span>
                    ) : null}
                    {turn.related_result_id ? (
                      <span className="video-thread-workbench__meta">
                        Result: {turn.related_result_id}
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className={getPanelClassName("process")}>
        <h2>Process and agent activity</h2>
        <div className="video-thread-workbench__process">
          {surface.process.runs.map((run) => (
            <article key={run.run_id} className="video-thread-workbench__run">
              <div className="video-thread-workbench__turn-row">
                <strong>{run.role}</strong>
                <span>{run.phase || run.status}</span>
              </div>
              {run.output_summary ? <p>{run.output_summary}</p> : null}
            </article>
          ))}
        </div>
      </section>

      <section className={getPanelClassName("participants")}>
        <h2>Participants</h2>
        <div className="video-thread-workbench__conversation">
          {surface.participants.items.map((participant) => (
            <article key={participant.participant_id} className="video-thread-workbench__turn">
              <div className="video-thread-workbench__turn-row">
                <strong>{participant.display_name}</strong>
                <span>{participant.role}</span>
              </div>
              {participant.agent_id ? <p>{participant.agent_id}</p> : null}
              {participantManagement.can_remove &&
              participantManagement.removable_participant_ids.includes(participant.participant_id) ? (
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
            <strong>Owner participant controls</strong>
            <span>{participantManagement.can_manage ? "Active" : "View only"}</span>
          </div>
          <p>{participantManagement.context_hint || participantManagement.disabled_reason}</p>
          <div className="video-thread-workbench__participant-form">
            <label className="video-thread-workbench__label" htmlFor="participant-agent-id">
              Participant agent id
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
              Participant display name
            </label>
            <input
              id="participant-display-name"
              className="video-thread-workbench__input"
              value={participantDraft.displayName}
              placeholder="Reviewer"
              onChange={(event) => onParticipantDraftChange("displayName", event.target.value)}
              disabled={participantSubmitting || !participantManagement.can_invite}
            />
            <label className="video-thread-workbench__label" htmlFor="participant-role">
              Participant role
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

      <section className={getPanelClassName("composer")}>
        <h2>Composer</h2>
        <div className="video-thread-workbench__actions">
          {surface.actions.items.map((action) => (
            <button
              key={action.action_id}
              type="button"
              className={`video-thread-workbench__action ${
                activeActionId === action.action_id ? "video-thread-workbench__action--selected" : ""
              }`}
              onClick={() => onSelectAction(action.action_id)}
              disabled={action.disabled || submitting}
              title={action.disabled ? action.disabled_reason : action.description}
            >
              {action.label}
            </button>
          ))}
        </div>
        {selectedAction?.description ? <p>{selectedAction.description}</p> : null}
        <label className="video-thread-workbench__label" htmlFor="video-thread-composer">
          {selectedAction?.label || "Add note"}
        </label>
        <textarea
          id="video-thread-composer"
          className="video-thread-workbench__composer"
          rows={4}
          value={draft}
          placeholder={surface.composer.placeholder}
          onChange={(event) => onDraftChange(event.target.value)}
          disabled={submitting || surface.composer.disabled}
        />
        {surface.composer.context_hint ? <p>{surface.composer.context_hint}</p> : null}
        {activeComposerTarget?.summary ? <p>{activeComposerTarget.summary}</p> : null}
        {activeComposerTarget?.addressed_display_name || activeComposerTarget?.addressed_participant_id ? (
          <p>
            Reply target:{" "}
            {activeComposerTarget.addressed_display_name ||
              activeComposerTarget.addressed_participant_id}
          </p>
        ) : null}
        <div className="video-thread-workbench__composer-footer">
          <div className="video-thread-workbench__composer-strategy">
            <span>Focus: {surface.render_contract.default_focus_panel}</span>
            <span>Expanded: {expandedPanelsLabel}</span>
          </div>
          <button
            type="button"
            className={`video-thread-workbench__submit video-thread-workbench__submit--${surface.render_contract.sticky_primary_action_emphasis}`}
            onClick={onSubmit}
            disabled={submitting || surface.composer.disabled || !draft.trim() || selectedAction?.disabled}
          >
            {surface.composer.submit_label}
          </button>
        </div>
      </section>
    </section>
  );
}
