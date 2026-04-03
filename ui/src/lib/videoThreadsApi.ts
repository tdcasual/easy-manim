import { requestJson } from "./api";

export type VideoThreadHeader = {
  thread_id: string;
  title: string;
  status: string;
  current_iteration_id?: string | null;
  selected_result_id?: string | null;
};

export type VideoThreadCurrentFocus = {
  current_iteration_id?: string | null;
  current_iteration_goal?: string | null;
  current_result_id?: string | null;
  current_result_summary?: string | null;
  current_result_author_display_name?: string | null;
  current_result_author_role?: string | null;
  current_result_selection_reason?: string | null;
};

export type VideoThreadResponsibility = {
  owner_action_required?: string | null;
  expected_agent_role?: string | null;
  expected_agent_id?: string | null;
};

export type VideoThreadSelectionSummary = {
  title: string;
  summary: string;
  selected_result_id?: string | null;
  author_display_name?: string | null;
  author_role?: string | null;
};

export type VideoThreadLatestExplanation = {
  title: string;
  summary: string;
  turn_id?: string | null;
  speaker_display_name?: string | null;
  speaker_role?: string | null;
};

export type VideoThreadAuthorship = {
  title: string;
  summary: string;
  primary_agent_display_name?: string | null;
  primary_agent_role?: string | null;
  source_iteration_id?: string | null;
  source_run_id?: string | null;
  source_turn_id?: string | null;
};

export type VideoThreadDecisionNote = {
  note_id: string;
  note_kind: "selection_rationale" | "agent_explanation" | "iteration_goal";
  title: string;
  summary: string;
  emphasis: "primary" | "supporting" | "context";
  source_iteration_id?: string | null;
  source_turn_id?: string | null;
  source_result_id?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
};

export type VideoThreadArtifactLineageItem = {
  lineage_id: string;
  iteration_id?: string | null;
  from_result_id?: string | null;
  to_result_id?: string | null;
  change_summary: string;
  change_reason: string;
  trigger_turn_id?: string | null;
  trigger_label?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
  emphasis: "primary" | "supporting" | "context";
  status: "selected" | "active" | "superseded" | "origin";
};

export type VideoThreadRationaleSnapshot = {
  snapshot_id: string;
  iteration_id?: string | null;
  snapshot_kind: "owner_goal" | "agent_explanation" | "selection_rationale";
  title: string;
  summary: string;
  source_turn_id?: string | null;
  source_result_id?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
  emphasis: "primary" | "supporting" | "context";
  status: "current" | "archived";
};

export type VideoThreadIterationCompare = {
  title: string;
  summary: string;
  previous_iteration_id?: string | null;
  current_iteration_id?: string | null;
  previous_result_id?: string | null;
  current_result_id?: string | null;
  change_summary: string;
  rationale_shift_summary: string;
  continuity_status: "new" | "preserved" | "changed" | "unknown";
  continuity_summary: string;
};

export type VideoThreadDiscussionReply = {
  turn_id: string;
  title: string;
  summary: string;
  speaker_display_name?: string | null;
  speaker_role?: string | null;
  intent_type?: string | null;
  related_result_id?: string | null;
};

export type VideoThreadDiscussionGroup = {
  group_id: string;
  iteration_id?: string | null;
  prompt_turn_id: string;
  prompt_title: string;
  prompt_summary: string;
  prompt_intent_type?: string | null;
  prompt_actor_display_name?: string | null;
  prompt_actor_role?: string | null;
  related_result_id?: string | null;
  status: "open" | "answered";
  replies: VideoThreadDiscussionReply[];
};

export type VideoThreadDiscussionRuntime = {
  title: string;
  summary: string;
  active_iteration_id?: string | null;
  active_discussion_group_id?: string | null;
  continuity_scope: "iteration" | "result" | "thread";
  reply_policy: "continue_thread" | "start_new_thread" | "agent_choice";
  default_intent_type?: string | null;
  default_reply_to_turn_id?: string | null;
  default_related_result_id?: string | null;
  addressed_participant_id?: string | null;
  addressed_agent_id?: string | null;
  addressed_display_name?: string | null;
  suggested_follow_up_modes: string[];
  active_thread_title?: string | null;
  active_thread_summary: string;
  latest_owner_turn_id?: string | null;
  latest_agent_turn_id?: string | null;
  latest_agent_summary: string;
};

export type VideoThreadParticipantRuntimeContributor = {
  participant_id?: string | null;
  agent_id?: string | null;
  display_name: string;
  role?: string | null;
  contribution_kind: "expected_responder" | "recent_run" | "recent_reply";
  summary: string;
};

export type VideoThreadParticipantRuntime = {
  title: string;
  summary: string;
  active_iteration_id?: string | null;
  expected_participant_id?: string | null;
  expected_agent_id?: string | null;
  expected_display_name?: string | null;
  expected_role?: string | null;
  continuity_mode:
    | "keep_current_participant"
    | "invite_new_participant"
    | "agent_choice";
  follow_up_target_locked: boolean;
  recent_contributors: VideoThreadParticipantRuntimeContributor[];
};

export type VideoThreadProductionJournalEntry = {
  entry_id: string;
  entry_kind: "iteration" | "run" | "result";
  title: string;
  summary: string;
  stage: string;
  status: string;
  iteration_id?: string | null;
  task_id?: string | null;
  run_id?: string | null;
  result_id?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
  resource_refs: string[];
  created_at?: string | null;
};

export type VideoThreadNextRecommendedMove = {
  title: string;
  summary: string;
  recommended_action_id?: string | null;
  recommended_action_label?: string | null;
  owner_action_required?: string | null;
  tone: "neutral" | "active" | "attention";
};

export type VideoThreadIterationCard = {
  iteration_id: string;
  title: string;
  goal: string;
  status: string;
  resolution_state: string;
  requested_action?: string | null;
  result_summary?: string | null;
  responsible_role?: string | null;
  responsible_agent_id?: string | null;
};

export type VideoThreadIterationDetailSummary = {
  title: string;
  summary: string;
  selected_iteration_id?: string | null;
  resource_uri?: string | null;
  turn_count: number;
  run_count: number;
  result_count: number;
  execution_summary: VideoThreadIterationExecutionSummary;
};

export type VideoThreadIterationExecutionSummary = {
  title: string;
  summary: string;
  task_id?: string | null;
  run_id?: string | null;
  status: string;
  phase?: string | null;
  agent_id?: string | null;
  agent_display_name?: string | null;
  agent_role?: string | null;
  result_id?: string | null;
  discussion_group_id?: string | null;
  reply_to_turn_id?: string | null;
  latest_owner_turn_id?: string | null;
  latest_agent_turn_id?: string | null;
  is_active: boolean;
};

export type VideoThreadComposerTarget = {
  iteration_id?: string | null;
  result_id?: string | null;
  addressed_participant_id?: string | null;
  addressed_agent_id?: string | null;
  addressed_display_name?: string | null;
  agent_role?: string | null;
  agent_display_name?: string | null;
  summary: string;
};

export type VideoThreadIterationDetailTurn = {
  turn_id: string;
  turn_type: string;
  title: string;
  summary: string;
  intent_type?: string | null;
  reply_to_turn_id?: string | null;
  related_result_id?: string | null;
  addressed_participant_id?: string | null;
  addressed_agent_id?: string | null;
  addressed_display_name?: string | null;
  speaker_display_name?: string | null;
  speaker_role?: string | null;
  created_at?: string | null;
};

export type VideoThreadIterationDetailRun = {
  run_id: string;
  agent_id?: string | null;
  agent_display_name?: string | null;
  role: string;
  status: string;
  phase?: string | null;
  output_summary?: string | null;
  task_id?: string | null;
  created_at?: string | null;
};

export type VideoThreadIterationDetailResult = {
  result_id: string;
  status: string;
  result_summary: string;
  selected: boolean;
  video_resource?: string | null;
  created_at?: string | null;
};

export type VideoThreadIterationDetail = {
  thread_id: string;
  iteration_id: string;
  title: string;
  summary: string;
  execution_summary: VideoThreadIterationExecutionSummary;
  composer_target: VideoThreadComposerTarget;
  iteration: {
    iteration_id: string;
    thread_id: string;
    parent_iteration_id?: string | null;
    goal: string;
    requested_action?: string | null;
    preserve_working_parts?: boolean | null;
    status: string;
    resolution_state: string;
    focus_summary?: string | null;
    selected_result_id?: string | null;
    source_result_id?: string | null;
    initiated_by_turn_id?: string | null;
    responsible_role?: string | null;
    responsible_agent_id?: string | null;
  };
  turns: VideoThreadIterationDetailTurn[];
  runs: VideoThreadIterationDetailRun[];
  results: VideoThreadIterationDetailResult[];
};

export type VideoThreadConversationTurn = {
  turn_id: string;
  iteration_id: string;
  title: string;
  summary: string;
  intent_type?: string | null;
  reply_to_turn_id?: string | null;
  related_result_id?: string | null;
  addressed_participant_id?: string | null;
  addressed_agent_id?: string | null;
  speaker_type: string;
  speaker_role?: string | null;
};

export type VideoThreadProcessRun = {
  run_id: string;
  iteration_id: string;
  task_id?: string | null;
  role: string;
  status: string;
  phase?: string | null;
  output_summary?: string | null;
};

export type VideoThreadHistoryCard = {
  card_id: string;
  card_type: "result_selection" | "agent_explanation" | "process_update" | "owner_request";
  title: string;
  summary: string;
  iteration_id?: string | null;
  intent_type?: string | null;
  reply_to_turn_id?: string | null;
  related_result_id?: string | null;
  actor_display_name?: string | null;
  actor_role?: string | null;
  emphasis: "primary" | "supporting" | "context";
};

export type VideoThreadParticipant = {
  participant_id: string;
  participant_type: string;
  agent_id?: string | null;
  role: string;
  display_name: string;
  capabilities?: string[];
};

export type VideoThreadParticipantManagement = {
  can_manage: boolean;
  can_invite: boolean;
  can_remove: boolean;
  invite_label: string;
  invite_placeholder: string;
  default_role: string;
  default_capabilities: string[];
  remove_label: string;
  removable_participant_ids: string[];
  disabled_reason?: string;
  context_hint: string;
};

export type VideoThreadAction = {
  action_id: string;
  label: string;
  description: string;
  tone: "strong" | "neutral" | "muted";
  disabled: boolean;
  disabled_reason?: string;
};

export type VideoThreadSurface = {
  thread_header: VideoThreadHeader;
  thread_summary: string;
  current_focus: VideoThreadCurrentFocus;
  selection_summary: VideoThreadSelectionSummary;
  latest_explanation: VideoThreadLatestExplanation;
  decision_notes: {
    title: string;
    items: VideoThreadDecisionNote[];
  };
  artifact_lineage: {
    title: string;
    summary: string;
    selected_result_id?: string | null;
    items: VideoThreadArtifactLineageItem[];
  };
  rationale_snapshots: {
    title: string;
    summary: string;
    current_iteration_id?: string | null;
    items: VideoThreadRationaleSnapshot[];
  };
  iteration_compare: VideoThreadIterationCompare;
  authorship: VideoThreadAuthorship;
  next_recommended_move: VideoThreadNextRecommendedMove;
  responsibility: VideoThreadResponsibility;
  iteration_workbench: {
    iterations: VideoThreadIterationCard[];
    selected_iteration_id?: string | null;
    latest_iteration_id?: string | null;
  };
  iteration_detail: VideoThreadIterationDetailSummary;
  conversation: {
    turns: VideoThreadConversationTurn[];
  };
  history: {
    cards: VideoThreadHistoryCard[];
  };
  production_journal: {
    title: string;
    summary: string;
    entries: VideoThreadProductionJournalEntry[];
  };
  discussion_groups: {
    groups: VideoThreadDiscussionGroup[];
  };
  discussion_runtime: VideoThreadDiscussionRuntime;
  participant_runtime: VideoThreadParticipantRuntime;
  process: {
    runs: VideoThreadProcessRun[];
  };
  participants: {
    items: VideoThreadParticipant[];
    management: VideoThreadParticipantManagement;
  };
  actions: {
    items: VideoThreadAction[];
  };
  composer: {
    placeholder: string;
    submit_label: string;
    disabled: boolean;
    disabled_reason?: string;
    context_hint: string;
    target: VideoThreadComposerTarget;
  };
  render_contract: {
    default_focus_panel: string;
    panel_tone: "neutral" | "active" | "attention" | "resolved";
    display_priority: "normal" | "high";
    badge_order: string[];
    panel_order: string[];
    default_expanded_panels: string[];
    sticky_primary_action_id?: string | null;
    sticky_primary_action_emphasis: "strong" | "normal" | "subtle";
    panel_presentations: Array<{
      panel_id: string;
      tone: "accent" | "neutral" | "attention" | "subtle";
      emphasis: "primary" | "supporting" | "context";
      default_open: boolean;
      collapsible: boolean;
    }>;
  };
};

export type AppendVideoTurnRequest = {
  iteration_id: string;
  title: string;
  summary?: string;
  addressed_participant_id?: string;
  reply_to_turn_id?: string;
  related_result_id?: string;
};

export type RequestVideoRevisionRequest = {
  summary: string;
  preserve_working_parts?: boolean;
};

export type RequestVideoExplanationRequest = {
  summary: string;
};

export type SelectVideoResultRequest = {
  result_id: string;
};

export type VideoThreadParticipantUpsertRequest = {
  participant_id: string;
  participant_type: string;
  agent_id?: string | null;
  role: string;
  display_name: string;
  capabilities?: string[];
};

export async function getVideoThreadSurface(
  threadId: string,
  token: string
): Promise<VideoThreadSurface> {
  return requestJson<VideoThreadSurface>(`/api/video-threads/${encodeURIComponent(threadId)}/surface`, token, {
    method: "GET",
  });
}

export async function getVideoThreadIteration(
  threadId: string,
  iterationId: string,
  token: string
): Promise<VideoThreadIterationDetail> {
  return requestJson<VideoThreadIterationDetail>(
    `/api/video-threads/${encodeURIComponent(threadId)}/iterations/${encodeURIComponent(iterationId)}`,
    token,
    {
      method: "GET",
    }
  );
}

export async function appendVideoTurn(
  threadId: string,
  payload: AppendVideoTurnRequest,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/video-threads/${encodeURIComponent(threadId)}/turns`,
    token,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function requestVideoRevision(
  threadId: string,
  iterationId: string,
  payload: RequestVideoRevisionRequest,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/video-threads/${encodeURIComponent(threadId)}/iterations/${encodeURIComponent(iterationId)}/request-revision`,
    token,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function requestVideoExplanation(
  threadId: string,
  iterationId: string,
  payload: RequestVideoExplanationRequest,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/video-threads/${encodeURIComponent(threadId)}/iterations/${encodeURIComponent(iterationId)}/request-explanation`,
    token,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function selectVideoResult(
  threadId: string,
  iterationId: string,
  payload: SelectVideoResultRequest,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/video-threads/${encodeURIComponent(threadId)}/iterations/${encodeURIComponent(iterationId)}/select-result`,
    token,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function listVideoThreadParticipants(
  threadId: string,
  token: string
): Promise<{ thread_id: string; items: VideoThreadParticipant[] }> {
  return requestJson<{ thread_id: string; items: VideoThreadParticipant[] }>(
    `/api/video-threads/${encodeURIComponent(threadId)}/participants`,
    token,
    {
      method: "GET",
    }
  );
}

export async function upsertVideoThreadParticipant(
  threadId: string,
  payload: VideoThreadParticipantUpsertRequest,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/video-threads/${encodeURIComponent(threadId)}/participants`,
    token,
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function removeVideoThreadParticipant(
  threadId: string,
  participantId: string,
  token: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/api/video-threads/${encodeURIComponent(threadId)}/participants/${encodeURIComponent(participantId)}`,
    token,
    {
      method: "DELETE",
    }
  );
}
