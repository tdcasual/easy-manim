import type { VideoThreadComposerTarget, VideoThreadSurface } from "../../lib/videoThreadsApi";
import { useI18n } from "../../app/locale";
import "./VideoThreadWorkbench.css";

type ThreadDiscussionPanelProps = {
  surface: VideoThreadSurface;
  activeActionId: string | null;
  activeComposerTarget: VideoThreadComposerTarget | null;
  replyToTurnId: string | null;
  draft: string;
  submitting: boolean;
  onDraftChange: (value: string) => void;
  onSelectAction: (actionId: string) => void;
  onSubmit: () => void;
};

export function ThreadDiscussionPanel({
  surface,
  activeActionId,
  activeComposerTarget,
  replyToTurnId,
  draft,
  submitting,
  onDraftChange,
  onSelectAction,
  onSubmit,
}: ThreadDiscussionPanelProps) {
  const { t } = useI18n();
  const selectedAction =
    surface.actions.items.find((item) => item.action_id === activeActionId) ??
    surface.actions.items[0] ??
    null;
  const discussionRuntime = surface.discussion_runtime ?? {
    title: t("thread.discussion.title"),
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
  const composerResultId =
    activeComposerTarget?.result_id ?? discussionRuntime.default_related_result_id ?? null;
  const composerReplyToTurnId = replyToTurnId ?? discussionRuntime.default_reply_to_turn_id ?? null;
  const replyTarget =
    activeComposerTarget?.addressed_display_name ??
    activeComposerTarget?.addressed_participant_id ??
    discussionRuntime.addressed_display_name ??
    discussionRuntime.addressed_participant_id ??
    t("thread.discussion.agentChoice");

  return (
    <section
      aria-label={t("thread.discussion.ariaLabel")}
      className="thread-discussion-panel video-thread-workbench__panel video-thread-workbench__panel--tone-accent video-thread-workbench__panel--emphasis-primary video-thread-workbench__panel--open"
    >
      <div className="thread-discussion-panel__header">
        <div>
          <h2>{t("thread.discussion.title")}</h2>
          <p>
            {discussionRuntime.summary ||
              surface.composer.context_hint ||
              t("thread.discussion.empty")}
          </p>
        </div>
        <div className="video-thread-workbench__chip-list">
          <span className="video-thread-workbench__chip">
            {t("thread.discussion.threadLabel")}: {discussionRuntime.active_thread_title ?? t("thread.discussion.openDiscussion")}
          </span>
          <span className="video-thread-workbench__chip">Reply target: {replyTarget}</span>
          <span className="video-thread-workbench__chip">
            Iteration:{" "}
            {activeComposerTarget?.iteration_id ??
              discussionRuntime.active_iteration_id ??
              t("thread.discussion.threadWide")}
          </span>
        </div>
      </div>

      {discussionRuntime.active_thread_summary ? (
        <p>{discussionRuntime.active_thread_summary}</p>
      ) : null}

      <div className="thread-discussion-panel__context video-thread-workbench__intent-meta">
        <span className="video-thread-workbench__meta">
          {t("thread.discussion.replyToLabel")}: {composerReplyToTurnId ?? t("thread.discussion.startNewTurn")}
        </span>
        <span className="video-thread-workbench__meta">
          {t("thread.discussion.resultLabel")}: {composerResultId ?? t("thread.discussion.threadWide")}
        </span>
        <span className="video-thread-workbench__meta">
          {t("thread.discussion.continuityLabel")}: {discussionRuntime.continuity_scope}
        </span>
        <span className="video-thread-workbench__meta">
          {t("thread.discussion.replyPolicyLabel")}: {discussionRuntime.reply_policy}
        </span>
      </div>

      {surface.discussion_groups.groups.length ? (
        <div className="thread-discussion-panel__stack">
          {surface.discussion_groups.groups.map((group) => (
            <article key={group.group_id} className="video-thread-workbench__discussion-group">
              <div className="video-thread-workbench__turn-row">
                <strong>{group.prompt_title}</strong>
                <span>{group.status}</span>
              </div>
              {group.prompt_summary ? <p>{group.prompt_summary}</p> : null}
              <div className="video-thread-workbench__intent-meta">
                <span className="video-thread-workbench__meta">
                  {t("thread.discussion.promptByLabel")}: {group.prompt_actor_display_name ?? group.prompt_actor_role ?? t("thread.discussion.owner")}
                </span>
                {group.prompt_intent_type ? (
                  <span className="video-thread-workbench__meta">
                    {t("thread.discussion.intentLabel")}: {group.prompt_intent_type}
                  </span>
                ) : null}
                {group.related_result_id ? (
                  <span className="video-thread-workbench__meta">
                    Result: {group.related_result_id}
                  </span>
                ) : null}
              </div>
              {group.replies.length ? (
                <div className="video-thread-workbench__reply-list">
                  {group.replies.map((reply) => (
                    <article key={reply.turn_id} className="video-thread-workbench__reply">
                      <div className="video-thread-workbench__turn-row">
                        <strong>{reply.title}</strong>
                        <span>{reply.speaker_display_name ?? reply.speaker_role ?? t("thread.discussion.agent")}</span>
                      </div>
                      {reply.summary ? <p>{reply.summary}</p> : null}
                    </article>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}

      {surface.conversation.turns.length ? (
        <div className="thread-discussion-panel__stack">
          {surface.conversation.turns.map((turn) => (
            <article key={turn.turn_id} className="video-thread-workbench__turn">
              <div className="video-thread-workbench__turn-row">
                <strong>{turn.title}</strong>
                <span>{turn.speaker_role ?? turn.speaker_type}</span>
              </div>
              {turn.summary ? <p>{turn.summary}</p> : null}
              <div className="video-thread-workbench__intent-meta">
                {turn.intent_type ? (
                  <span className="video-thread-workbench__meta">Intent: {turn.intent_type}</span>
                ) : null}
                {turn.reply_to_turn_id ? (
                  <span className="video-thread-workbench__meta">
                    {t("thread.discussion.repliesToLabel")}: {turn.reply_to_turn_id}
                  </span>
                ) : null}
                {turn.related_result_id ? (
                  <span className="video-thread-workbench__meta">
                    Result: {turn.related_result_id}
                  </span>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      <div className="thread-discussion-panel__composer">
        <div className="video-thread-workbench__actions">
          {surface.actions.items.map((action) => (
            <button
              key={action.action_id}
              type="button"
              className={`video-thread-workbench__action ${
                activeActionId === action.action_id
                  ? "video-thread-workbench__action--selected"
                  : ""
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
        <label className="video-thread-workbench__label" htmlFor="video-thread-discussion-composer">
          {selectedAction?.label || t("thread.discussion.addNote")}
        </label>
        <textarea
          id="video-thread-discussion-composer"
          className="video-thread-workbench__composer"
          rows={4}
          value={draft}
          placeholder={surface.composer.placeholder}
          onChange={(event) => onDraftChange(event.target.value)}
          disabled={submitting || surface.composer.disabled}
        />
        {surface.composer.context_hint ? <p>{surface.composer.context_hint}</p> : null}
        {activeComposerTarget?.summary ? <p>{activeComposerTarget.summary}</p> : null}
        <div className="video-thread-workbench__composer-footer">
          <div className="video-thread-workbench__composer-strategy">
            <span>{t("thread.composer.modeLabel")}: {selectedAction?.label || t("thread.discussion.addNote")}</span>
            <span>{t("thread.composer.replyTargetLabel")}: {replyTarget}</span>
          </div>
          <button
            type="button"
            className={`video-thread-workbench__submit video-thread-workbench__submit--${surface.render_contract.sticky_primary_action_emphasis}`}
            onClick={onSubmit}
            disabled={
              submitting || surface.composer.disabled || !draft.trim() || selectedAction?.disabled
            }
          >
            {surface.composer.submit_label}
          </button>
        </div>
      </div>
    </section>
  );
}
