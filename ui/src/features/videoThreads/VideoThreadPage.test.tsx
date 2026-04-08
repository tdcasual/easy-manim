import userEvent from "@testing-library/user-event";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { ToastProvider } from "../../components/Toast";
import { writeSessionToken } from "../../lib/session";
import { VideoThreadPage } from "./VideoThreadPage";

function createThreadSurface(overrides: Record<string, any> = {}) {
  const base = {
    thread_header: {
      thread_id: "thread-1",
      title: "Circle explainer",
      status: "active",
      current_iteration_id: "iter-1",
      selected_result_id: "result-1",
    },
    thread_summary: "A durable collaboration thread for iterating on this video.",
    current_focus: {
      current_iteration_id: "iter-1",
      current_iteration_goal: "Slow the opener a little.",
      current_result_id: "result-1",
      current_result_summary: "Selected cut with a slower title entrance.",
      current_result_author_display_name: "Repairer",
      current_result_author_role: "repairer",
      current_result_selection_reason: "The current cut remains the preferred version.",
    },
    selection_summary: {
      title: "Why this version is selected",
      summary: "The current cut remains the preferred version.",
      selected_result_id: "result-1",
      author_display_name: "Repairer",
      author_role: "repairer",
    },
    latest_explanation: {
      title: "Latest visible explanation",
      summary: "The slower opener gives the title room to land.",
      turn_id: "turn-2",
      speaker_display_name: "Repairer",
      speaker_role: "repairer",
    },
    authorship: {
      title: "Who shaped this version",
      summary: "Repairer shaped the latest selected cut.",
      primary_agent_display_name: "Repairer",
      primary_agent_role: "repairer",
      source_iteration_id: "iter-1",
      source_turn_id: "turn-2",
    },
    decision_notes: { title: "Decision Notes", items: [] },
    artifact_lineage: {
      title: "Artifact Lineage",
      summary: "",
      selected_result_id: "result-1",
      items: [],
    },
    rationale_snapshots: {
      title: "Rationale Snapshots",
      summary: "",
      current_iteration_id: "iter-1",
      items: [],
    },
    iteration_compare: {
      title: "Iteration Compare",
      summary: "",
      previous_iteration_id: null,
      current_iteration_id: "iter-1",
      previous_result_id: null,
      current_result_id: "result-1",
      change_summary: "",
      rationale_shift_summary: "",
      continuity_status: "preserved",
      continuity_summary: "",
    },
    next_recommended_move: {
      title: "Recommended next move",
      summary: "Record focused feedback for the shaping agent.",
      recommended_action_id: "discuss",
      recommended_action_label: "Add note",
      owner_action_required: "share_feedback",
      tone: "active",
    },
    responsibility: {
      owner_action_required: "share_feedback",
      expected_agent_role: "repairer",
      expected_agent_id: "repairer-1",
    },
    iteration_workbench: {
      selected_iteration_id: "iter-1",
      latest_iteration_id: "iter-1",
      iterations: [
        {
          iteration_id: "iter-1",
          title: "Slow the opener",
          goal: "Slow the opener a little.",
          status: "active",
          resolution_state: "open",
          requested_action: "revise",
          result_summary: "Selected cut with a slower title entrance.",
          responsible_role: "repairer",
          responsible_agent_id: "repairer-1",
        },
      ],
    },
    iteration_detail: {
      title: "Iteration Detail",
      summary: "This iteration currently tracks one visible turn, no runs, and one result.",
      selected_iteration_id: "iter-1",
      resource_uri: "video-thread://thread-1/iterations/iter-1.json",
      turn_count: 1,
      run_count: 0,
      result_count: 1,
    },
    conversation: { turns: [] },
    history: { cards: [] },
    production_journal: { title: "Production Journal", summary: "", entries: [] },
    discussion_groups: { groups: [] },
    discussion_runtime: {
      title: "Discussion Runtime",
      summary: "Discuss the currently selected cut.",
      active_iteration_id: "iter-1",
      active_discussion_group_id: null,
      continuity_scope: "iteration",
      reply_policy: "continue_thread",
      default_intent_type: "discuss",
      default_reply_to_turn_id: "turn-1",
      default_related_result_id: "result-1",
      addressed_participant_id: "repairer-1",
      addressed_agent_id: "repairer-1",
      addressed_display_name: "Repairer",
      suggested_follow_up_modes: [],
      active_thread_title: "Version review",
      active_thread_summary: "Choose the cut you want to carry forward.",
      latest_owner_turn_id: "turn-1",
      latest_agent_turn_id: null,
      latest_agent_summary: "",
    },
    participant_runtime: {
      title: "Participant Runtime",
      summary: "",
      active_iteration_id: "iter-1",
      expected_participant_id: "repairer-1",
      expected_agent_id: "repairer-1",
      expected_display_name: "Repairer",
      expected_role: "repairer",
      continuity_mode: "keep_current_participant",
      follow_up_target_locked: true,
      recent_contributors: [],
    },
    process: { runs: [] },
    participants: {
      items: [
        {
          participant_id: "owner",
          participant_type: "owner",
          role: "owner",
          display_name: "Owner",
          agent_id: "agent-a",
        },
        {
          participant_id: "repairer-1",
          participant_type: "agent",
          role: "repairer",
          display_name: "Repairer",
          agent_id: "repairer-1",
        },
      ],
      management: {
        can_manage: true,
        can_invite: true,
        can_remove: true,
        invite_label: "Invite participant",
        invite_placeholder: "Agent id",
        default_role: "reviewer",
        default_capabilities: ["review_bundle:read"],
        remove_label: "Remove participant",
        removable_participant_ids: ["repairer-1"],
        disabled_reason: "",
        context_hint: "Invite reviewers or helper agents into this thread.",
      },
    },
    actions: {
      items: [
        {
          action_id: "request_revision",
          label: "Request revision",
          description: "Create the next revision from the selected result and current goal.",
          tone: "strong",
          disabled: false,
          disabled_reason: "",
        },
        {
          action_id: "request_explanation",
          label: "Ask why",
          description: "Request a product-safe explanation for the current direction.",
          tone: "neutral",
          disabled: false,
          disabled_reason: "",
        },
        {
          action_id: "discuss",
          label: "Add note",
          description: "Record feedback for the current shaping agent.",
          tone: "muted",
          disabled: false,
          disabled_reason: "",
        },
      ],
    },
    composer: {
      placeholder: "Ask why this version was made or request the next change.",
      submit_label: "Send",
      disabled: false,
      disabled_reason: "",
      context_hint: "The selected cut is ready for focused follow-up.",
      target: {
        iteration_id: "iter-1",
        result_id: "result-1",
        addressed_participant_id: "repairer-1",
        addressed_agent_id: "repairer-1",
        addressed_display_name: "Repairer",
        agent_role: "repairer",
        agent_display_name: "Repairer",
        summary:
          "New messages will attach to iter-1, stay anchored to result-1, and hand off to Repairer.",
      },
    },
    render_contract: {
      default_focus_panel: "composer",
      panel_tone: "active",
      display_priority: "normal",
      badge_order: ["owner_action_required"],
      panel_order: ["composer", "iteration_detail"],
      default_expanded_panels: ["composer", "iteration_detail"],
      sticky_primary_action_id: "discuss",
      sticky_primary_action_emphasis: "normal",
      panel_presentations: [
        {
          panel_id: "iteration_detail",
          tone: "neutral",
          emphasis: "supporting",
          default_open: true,
          collapsible: true,
        },
      ],
    },
  };

  return {
    ...base,
    ...overrides,
    thread_header: { ...base.thread_header, ...overrides.thread_header },
    current_focus: { ...base.current_focus, ...overrides.current_focus },
    selection_summary: { ...base.selection_summary, ...overrides.selection_summary },
    latest_explanation: { ...base.latest_explanation, ...overrides.latest_explanation },
    authorship: { ...base.authorship, ...overrides.authorship },
    decision_notes: { ...base.decision_notes, ...overrides.decision_notes },
    artifact_lineage: { ...base.artifact_lineage, ...overrides.artifact_lineage },
    rationale_snapshots: { ...base.rationale_snapshots, ...overrides.rationale_snapshots },
    iteration_compare: { ...base.iteration_compare, ...overrides.iteration_compare },
    next_recommended_move: { ...base.next_recommended_move, ...overrides.next_recommended_move },
    responsibility: { ...base.responsibility, ...overrides.responsibility },
    iteration_workbench: { ...base.iteration_workbench, ...overrides.iteration_workbench },
    iteration_detail: { ...base.iteration_detail, ...overrides.iteration_detail },
    conversation: { ...base.conversation, ...overrides.conversation },
    history: { ...base.history, ...overrides.history },
    production_journal: { ...base.production_journal, ...overrides.production_journal },
    discussion_groups: { ...base.discussion_groups, ...overrides.discussion_groups },
    discussion_runtime: { ...base.discussion_runtime, ...overrides.discussion_runtime },
    participant_runtime: { ...base.participant_runtime, ...overrides.participant_runtime },
    process: { ...base.process, ...overrides.process },
    participants: {
      ...base.participants,
      ...overrides.participants,
      management: {
        ...base.participants.management,
        ...(overrides.participants?.management ?? {}),
      },
    },
    actions: { ...base.actions, ...overrides.actions },
    composer: {
      ...base.composer,
      ...overrides.composer,
      target: {
        ...base.composer.target,
        ...(overrides.composer?.target ?? {}),
      },
    },
    render_contract: { ...base.render_contract, ...overrides.render_contract },
  };
}

function createIterationDetail(overrides: Record<string, any> = {}) {
  const base = {
    thread_id: "thread-1",
    iteration_id: "iter-1",
    title: "Iteration Detail",
    summary: "Initial iteration detail.",
    execution_summary: {
      title: "Execution Summary",
      summary: "Repairer is currently repairing for task task-1 while shaping result result-1.",
      task_id: "task-1",
      run_id: "thread-run:task-1",
      status: "running",
      phase: "repairing",
      agent_id: "repairer-1",
      agent_display_name: "Repairer",
      agent_role: "repairer",
      result_id: "result-1",
      discussion_group_id: "group-turn-1",
      reply_to_turn_id: "turn-1",
      latest_owner_turn_id: "turn-1",
      latest_agent_turn_id: "turn-2",
      is_active: true,
    },
    composer_target: {
      iteration_id: "iter-1",
      result_id: "result-1",
      addressed_participant_id: "repairer-1",
      addressed_agent_id: "repairer-1",
      addressed_display_name: "Repairer",
      agent_role: "repairer",
      agent_display_name: "Repairer",
      summary:
        "New messages will attach to iter-1, stay anchored to result-1, and hand off to Repairer.",
    },
    iteration: {
      iteration_id: "iter-1",
      thread_id: "thread-1",
      goal: "Slow the opener a little.",
      requested_action: "revise",
      preserve_working_parts: true,
      status: "active",
      resolution_state: "open",
      selected_result_id: "result-1",
      source_result_id: null,
      responsible_role: "repairer",
      responsible_agent_id: "repairer-1",
    },
    turns: [],
    runs: [],
    results: [
      {
        result_id: "result-1",
        status: "ready",
        result_summary: "Selected cut with a slower title entrance.",
        selected: true,
        video_resource: "video-task://task-1/artifacts/final.mp4",
      },
    ],
  };

  return {
    ...base,
    ...overrides,
    execution_summary: { ...base.execution_summary, ...overrides.execution_summary },
    composer_target: { ...base.composer_target, ...overrides.composer_target },
    iteration: { ...base.iteration, ...overrides.iteration },
  };
}

test("video thread page renders the collaboration workbench from thread surface", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(
        JSON.stringify({
          thread_header: {
            thread_id: "thread-1",
            title: "Circle explainer",
            status: "active",
            current_iteration_id: "iter-2",
            selected_result_id: "result-2",
          },
          thread_summary: "A durable collaboration thread for iterating on this video.",
          current_focus: {
            current_iteration_id: "iter-2",
            current_iteration_goal: "Slow the opener and make the title entrance more deliberate.",
            current_result_id: "result-2",
            current_result_summary: "Selected cut with a slower title entrance.",
            current_result_author_display_name: "Repairer",
            current_result_author_role: "repairer",
            current_result_selection_reason:
              "This is the latest selected revision for the active iteration and remains aligned with the owner goal.",
          },
          selection_summary: {
            title: "Why this version is selected",
            summary:
              "This is the latest selected revision for the active iteration and remains aligned with the owner goal.",
            selected_result_id: "result-2",
            author_display_name: "Repairer",
            author_role: "repairer",
          },
          latest_explanation: {
            title: "Latest visible explanation",
            summary: "The current version favors the slower title entrance.",
            turn_id: "turn-2",
            speaker_display_name: "Repairer",
            speaker_role: "repairer",
          },
          authorship: {
            title: "Who shaped this version",
            summary:
              "Repairer is the latest visible agent shaping the selected cut for this iteration.",
            primary_agent_display_name: "Repairer",
            primary_agent_role: "repairer",
            source_iteration_id: "iter-2",
            source_run_id: "run-1",
            source_turn_id: "turn-2",
          },
          decision_notes: {
            title: "Decision Notes",
            items: [
              {
                note_id: "decision-selection",
                note_kind: "selection_rationale",
                title: "Why this version is selected",
                summary:
                  "This is the latest selected revision for the active iteration and remains aligned with the owner goal.",
                emphasis: "primary",
                source_iteration_id: "iter-2",
                source_turn_id: null,
                source_result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
              },
              {
                note_id: "decision-explanation",
                note_kind: "agent_explanation",
                title: "Latest visible explanation",
                summary: "The current version favors the slower title entrance.",
                emphasis: "supporting",
                source_iteration_id: "iter-2",
                source_turn_id: "turn-2",
                source_result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
              },
              {
                note_id: "decision-goal",
                note_kind: "iteration_goal",
                title: "Current iteration goal",
                summary: "Slow the opener and make the title entrance more deliberate.",
                emphasis: "supporting",
                source_iteration_id: "iter-2",
                source_turn_id: null,
                source_result_id: null,
                actor_display_name: "Owner",
                actor_role: "owner",
              },
            ],
          },
          artifact_lineage: {
            title: "Artifact Lineage",
            summary: "How the current video evolved across visible revisions.",
            selected_result_id: "result-2",
            items: [
              {
                lineage_id: "lineage-iter-1",
                iteration_id: "iter-1",
                from_result_id: null,
                to_result_id: "result-1",
                change_summary: "Initial cut with a brisk opener.",
                change_reason: "The original generation established the baseline geometry motion.",
                trigger_turn_id: "turn-0",
                trigger_label: "Owner started the thread",
                actor_display_name: "Planner",
                actor_role: "planner",
                emphasis: "context",
                status: "origin",
              },
              {
                lineage_id: "lineage-iter-2",
                iteration_id: "iter-2",
                from_result_id: "result-1",
                to_result_id: "result-2",
                change_summary: "Selected cut with a slower title entrance.",
                change_reason: "Slow the opener and make the title entrance more deliberate.",
                trigger_turn_id: "turn-1",
                trigger_label: "Owner requested revision",
                actor_display_name: "Repairer",
                actor_role: "repairer",
                emphasis: "primary",
                status: "selected",
              },
            ],
          },
          rationale_snapshots: {
            title: "Rationale Snapshots",
            summary: "Canonical product-safe why notes across iterations.",
            current_iteration_id: "iter-2",
            items: [
              {
                snapshot_id: "snapshot-iter-1",
                iteration_id: "iter-1",
                snapshot_kind: "owner_goal",
                title: "Original direction",
                summary: "draw a circle",
                source_turn_id: "turn-0",
                source_result_id: "result-1",
                actor_display_name: "Owner",
                actor_role: "owner",
                emphasis: "context",
                status: "archived",
              },
              {
                snapshot_id: "snapshot-iter-2",
                iteration_id: "iter-2",
                snapshot_kind: "selection_rationale",
                title: "Why the current revision is selected",
                summary:
                  "This is the latest selected revision for the active iteration and remains aligned with the owner goal.",
                source_turn_id: null,
                source_result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
                emphasis: "primary",
                status: "current",
              },
            ],
          },
          iteration_compare: {
            title: "Iteration Compare",
            summary:
              "Compare the current selected cut against the nearest earlier visible iteration.",
            previous_iteration_id: "iter-1",
            current_iteration_id: "iter-2",
            previous_result_id: "result-1",
            current_result_id: "result-2",
            change_summary: "Selected cut with a slower title entrance.",
            rationale_shift_summary:
              "The previous cut established the baseline circle motion. The current revision shifts toward a more deliberate title entrance because the owner asked to slow the opener.",
            continuity_status: "changed",
            continuity_summary:
              "Participant continuity changed from Planner to Repairer between the compared iterations.",
          },
          next_recommended_move: {
            title: "Recommended next move",
            summary:
              "Review the latest selected result, then request a focused revision or record a note.",
            recommended_action_id: "request_revision",
            recommended_action_label: "Request revision",
            owner_action_required: "review_latest_result",
            tone: "attention",
          },
          responsibility: {
            owner_action_required: "review_latest_result",
            expected_agent_role: "repairer",
            expected_agent_id: "repairer-1",
          },
          iteration_workbench: {
            selected_iteration_id: "iter-2",
            latest_iteration_id: "iter-2",
            iterations: [
              {
                iteration_id: "iter-1",
                title: "draw a circle",
                goal: "draw a circle",
                status: "closed",
                resolution_state: "resolved",
                requested_action: "generate",
                result_summary: "Initial cut",
                responsible_role: "planner",
                responsible_agent_id: "planner-1",
              },
              {
                iteration_id: "iter-2",
                title: "Slow the opener",
                goal: "Slow the opener and make the title entrance more deliberate.",
                status: "active",
                resolution_state: "open",
                requested_action: "revise",
                result_summary: "Selected cut with a slower title entrance.",
                responsible_role: "repairer",
                responsible_agent_id: "repairer-1",
              },
            ],
          },
          iteration_detail: {
            title: "Iteration Detail",
            summary:
              "Inspect the selected iteration to review its visible discussion, runs, and results.",
            selected_iteration_id: "iter-2",
            resource_uri: "video-thread://thread-1/iterations/iter-2.json",
            turn_count: 2,
            run_count: 1,
            result_count: 1,
          },
          conversation: {
            turns: [
              {
                turn_id: "turn-1",
                iteration_id: "iter-2",
                title: "Why this pacing?",
                summary: "Explain the slower opener.",
                intent_type: "discuss",
                reply_to_turn_id: null,
                related_result_id: "result-2",
                speaker_type: "owner",
                speaker_role: "owner",
              },
              {
                turn_id: "turn-2",
                iteration_id: "iter-2",
                title: "Visible explanation",
                summary: "The current version favors the slower title entrance.",
                intent_type: "request_explanation",
                reply_to_turn_id: "turn-1",
                related_result_id: "result-2",
                speaker_type: "agent",
                speaker_role: "repairer",
              },
            ],
          },
          history: {
            cards: [
              {
                card_id: "history-run-1",
                card_type: "process_update",
                title: "Repairer is refining this cut",
                summary: "Refining title timing.",
                iteration_id: "iter-2",
                intent_type: "request_revision",
                reply_to_turn_id: null,
                related_result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
                emphasis: "supporting",
              },
              {
                card_id: "history-turn-2",
                card_type: "agent_explanation",
                title: "Visible explanation",
                summary: "The current version favors the slower title entrance.",
                iteration_id: "iter-2",
                intent_type: "request_explanation",
                reply_to_turn_id: "turn-1",
                related_result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
                emphasis: "primary",
              },
              {
                card_id: "history-selection-2",
                card_type: "result_selection",
                title: "Selected result rationale",
                summary:
                  "This is the latest selected revision for the active iteration and remains aligned with the owner goal.",
                iteration_id: "iter-2",
                intent_type: "request_revision",
                reply_to_turn_id: null,
                related_result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
                emphasis: "supporting",
              },
            ],
          },
          production_journal: {
            title: "Production Journal",
            summary: "A stable, product-safe log of how this version was produced.",
            entries: [
              {
                entry_id: "journal-iter-2",
                entry_kind: "iteration",
                title: "Revision iteration opened",
                summary: "Slow the opener and make the title entrance more deliberate.",
                stage: "revision",
                status: "active",
                iteration_id: "iter-2",
                task_id: "task-2",
                run_id: null,
                result_id: null,
                actor_display_name: "Owner",
                actor_role: "owner",
                resource_refs: [],
              },
              {
                entry_id: "journal-run-1",
                entry_kind: "run",
                title: "Repairer is repairing this cut",
                summary: "Refining title timing.",
                stage: "execution",
                status: "running",
                iteration_id: "iter-2",
                task_id: "task-2",
                run_id: "run-1",
                result_id: null,
                actor_display_name: "Repairer",
                actor_role: "repairer",
                resource_refs: [],
              },
              {
                entry_id: "journal-result-2",
                entry_kind: "result",
                title: "Selected result recorded",
                summary: "Selected cut with a slower title entrance.",
                stage: "result",
                status: "ready",
                iteration_id: "iter-2",
                task_id: "task-2",
                run_id: null,
                result_id: "result-2",
                actor_display_name: "Repairer",
                actor_role: "repairer",
                resource_refs: ["video-task://task-2/artifacts/final.mp4"],
              },
            ],
          },
          discussion_groups: {
            groups: [
              {
                group_id: "group-turn-1",
                iteration_id: "iter-2",
                prompt_turn_id: "turn-1",
                prompt_title: "Why this pacing?",
                prompt_summary: "Explain the slower opener.",
                prompt_intent_type: "request_explanation",
                prompt_actor_display_name: "Owner",
                prompt_actor_role: "owner",
                related_result_id: "result-2",
                status: "answered",
                replies: [
                  {
                    turn_id: "turn-2",
                    title: "Visible explanation",
                    summary: "The current version favors the slower title entrance.",
                    speaker_display_name: "Repairer",
                    speaker_role: "repairer",
                    intent_type: "request_explanation",
                    related_result_id: "result-2",
                  },
                ],
              },
            ],
          },
          discussion_runtime: {
            title: "Discussion Runtime",
            summary:
              "Continue 'Why this pacing?' with Repairer while staying on the active iteration.",
            active_iteration_id: "iter-2",
            active_discussion_group_id: "group-turn-1",
            continuity_scope: "iteration",
            reply_policy: "continue_thread",
            default_intent_type: "discuss",
            default_reply_to_turn_id: "turn-1",
            default_related_result_id: "result-2",
            addressed_participant_id: "repairer-1",
            addressed_agent_id: "repairer-1",
            addressed_display_name: "Repairer",
            suggested_follow_up_modes: [
              "ask_why",
              "request_change",
              "preserve_direction",
              "branch_revision",
            ],
            active_thread_title: "Why this pacing?",
            active_thread_summary: "Explain the slower opener.",
            latest_owner_turn_id: "turn-1",
            latest_agent_turn_id: "turn-2",
            latest_agent_summary: "The current version favors the slower title entrance.",
          },
          participant_runtime: {
            title: "Participant Runtime",
            summary:
              "Repairer is currently expected to respond, while Planner also shaped the active iteration.",
            active_iteration_id: "iter-2",
            expected_participant_id: "repairer-1",
            expected_agent_id: "repairer-1",
            expected_display_name: "Repairer",
            expected_role: "repairer",
            continuity_mode: "keep_current_participant",
            follow_up_target_locked: true,
            recent_contributors: [
              {
                participant_id: "repairer-1",
                agent_id: "repairer-1",
                display_name: "Repairer",
                role: "repairer",
                contribution_kind: "expected_responder",
                summary: "Currently targeted for the next owner follow-up.",
              },
              {
                participant_id: null,
                agent_id: "planner-1",
                display_name: "Planner",
                role: "planner",
                contribution_kind: "recent_reply",
                summary: "Explained the slower opener.",
              },
            ],
          },
          process: {
            runs: [
              {
                run_id: "run-1",
                iteration_id: "iter-2",
                task_id: "task-2",
                role: "repairer",
                status: "running",
                phase: "repairing",
                output_summary: "Refining title timing.",
              },
            ],
          },
          participants: {
            items: [
              {
                participant_id: "owner",
                participant_type: "owner",
                role: "owner",
                display_name: "Owner",
              },
              {
                participant_id: "repairer-1",
                participant_type: "agent",
                role: "repairer",
                display_name: "Repairer",
                agent_id: "repairer-1",
              },
            ],
            management: {
              can_manage: true,
              can_invite: true,
              can_remove: true,
              invite_label: "Invite participant",
              invite_placeholder: "Agent id",
              default_role: "reviewer",
              default_capabilities: ["review_bundle:read"],
              remove_label: "Remove participant",
              removable_participant_ids: ["repairer-1"],
              disabled_reason: "",
              context_hint: "Invite reviewers or helper agents into this thread.",
            },
          },
          actions: {
            items: [
              {
                action_id: "request_revision",
                label: "Request revision",
                description: "Create the next revision from the selected result and current goal.",
                tone: "strong",
                disabled: false,
              },
              {
                action_id: "request_explanation",
                label: "Ask why",
                description: "Request a product-safe explanation for the current direction.",
                tone: "neutral",
                disabled: false,
              },
              {
                action_id: "discuss",
                label: "Add note",
                description: "Record context without creating a new revision immediately.",
                tone: "muted",
                disabled: false,
              },
            ],
          },
          composer: {
            placeholder: "Ask why this version was made or request the next change.",
            submit_label: "Send",
            disabled: false,
            context_hint: "The selected cut is ready for review or a focused revision request.",
            target: {
              iteration_id: "iter-2",
              result_id: "result-2",
              addressed_participant_id: "repairer-1",
              addressed_agent_id: "repairer-1",
              addressed_display_name: "Repairer",
              agent_role: "repairer",
              agent_display_name: "Repairer",
              summary:
                "New messages will attach to iter-2, stay anchored to result-2, and hand off to Repairer.",
            },
          },
          render_contract: {
            default_focus_panel: "next_recommended_move",
            panel_tone: "attention",
            display_priority: "high",
            badge_order: ["owner_action_required", "selected_result", "expected_agent_role"],
            panel_order: [
              "thread_header",
              "current_focus",
              "selection_summary",
              "latest_explanation",
              "decision_notes",
              "artifact_lineage",
              "rationale_snapshots",
              "iteration_compare",
              "next_recommended_move",
              "production_journal",
              "history",
              "iteration_workbench",
              "iteration_detail",
              "conversation",
              "participants",
              "process",
              "actions",
              "composer",
            ],
            default_expanded_panels: [
              "current_focus",
              "decision_notes",
              "artifact_lineage",
              "rationale_snapshots",
              "iteration_compare",
              "next_recommended_move",
              "production_journal",
              "history",
              "composer",
            ],
            sticky_primary_action_emphasis: "strong",
            panel_presentations: [
              {
                panel_id: "current_focus",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: false,
              },
              {
                panel_id: "next_recommended_move",
                tone: "attention",
                emphasis: "primary",
                default_open: true,
                collapsible: false,
              },
              {
                panel_id: "decision_notes",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "artifact_lineage",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "rationale_snapshots",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "iteration_compare",
                tone: "accent",
                emphasis: "primary",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "production_journal",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "history",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "iteration_detail",
                tone: "neutral",
                emphasis: "supporting",
                default_open: true,
                collapsible: true,
              },
              {
                panel_id: "composer",
                tone: "accent",
                emphasis: "primary",
                default_open: true,
                collapsible: false,
              },
            ],
            sticky_primary_action_id: "request_revision",
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (
      path === "/api/video-threads/thread-1/iterations/iter-2" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(
        JSON.stringify({
          thread_id: "thread-1",
          iteration_id: "iter-2",
          title: "Iteration Detail",
          summary: "This revision carries the slower opener and the selected title entrance.",
          composer_target: {
            iteration_id: "iter-2",
            result_id: "result-2",
            addressed_participant_id: "repairer-1",
            addressed_agent_id: "repairer-1",
            addressed_display_name: "Repairer",
            agent_role: "repairer",
            agent_display_name: "Repairer",
            summary:
              "New messages will attach to iter-2, stay anchored to result-2, and hand off to Repairer.",
          },
          iteration: {
            iteration_id: "iter-2",
            thread_id: "thread-1",
            parent_iteration_id: "iter-1",
            goal: "Slow the opener and make the title entrance more deliberate.",
            requested_action: "revise",
            preserve_working_parts: true,
            status: "active",
            resolution_state: "open",
            source_result_id: "result-1",
            selected_result_id: "result-2",
            responsible_role: "repairer",
            responsible_agent_id: "repairer-1",
          },
          turns: [
            {
              turn_id: "turn-1",
              turn_type: "owner_request",
              title: "Why this pacing?",
              summary: "Explain the slower opener.",
              intent_type: "request_explanation",
              reply_to_turn_id: null,
              related_result_id: "result-2",
              speaker_display_name: "Owner",
              speaker_role: "owner",
            },
            {
              turn_id: "turn-2",
              turn_type: "agent_explanation",
              title: "Visible explanation",
              summary: "The current version favors the slower title entrance.",
              intent_type: "request_explanation",
              reply_to_turn_id: "turn-1",
              related_result_id: "result-2",
              speaker_display_name: "Repairer",
              speaker_role: "repairer",
            },
          ],
          runs: [
            {
              run_id: "run-1",
              agent_id: "repairer-1",
              agent_display_name: "Repairer",
              role: "repairer",
              status: "running",
              phase: "repairing",
              output_summary: "Refining title timing.",
              task_id: "task-2",
            },
          ],
          results: [
            {
              result_id: "result-2",
              status: "ready",
              result_summary: "Selected cut with a slower title entrance.",
              selected: true,
              video_resource: "video-task://task-2/artifacts/final.mp4",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-2/result" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          task_id: "task-2",
          status: "completed",
          ready: true,
          summary: "Selected cut with a slower title entrance.",
          video_download_url: "/api/tasks/task-2/artifacts/final_video.mp4",
          script_download_url: "/api/tasks/task-2/artifacts/current_script.py",
          validation_report_download_url:
            "/api/tasks/task-2/artifacts/validations/validation_report_v1.json",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (
      path === "/api/video-threads/thread-1/iterations/iter-1" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(
        JSON.stringify({
          thread_id: "thread-1",
          iteration_id: "iter-1",
          title: "Iteration Detail",
          summary: "This is the origin iteration that established the brisk opener.",
          composer_target: {
            iteration_id: "iter-1",
            result_id: "result-1",
            addressed_participant_id: "planner-1",
            addressed_agent_id: "planner-1",
            addressed_display_name: "Planner",
            agent_role: "planner",
            agent_display_name: "Planner",
            summary:
              "New messages will attach to iter-1, stay anchored to result-1, and hand off to Planner.",
          },
          iteration: {
            iteration_id: "iter-1",
            thread_id: "thread-1",
            parent_iteration_id: null,
            goal: "draw a circle",
            requested_action: "generate",
            preserve_working_parts: null,
            status: "closed",
            resolution_state: "resolved",
            source_result_id: null,
            selected_result_id: "result-1",
            responsible_role: "planner",
            responsible_agent_id: "planner-1",
          },
          turns: [],
          runs: [],
          results: [
            {
              result_id: "result-1",
              status: "ready",
              result_summary: "Initial cut with a brisk opener.",
              selected: false,
              video_resource: "video-task://task-1/artifacts/final.mp4",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/videos/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/videos/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Circle explainer" })).toBeInTheDocument();
  const selectedVersion = await screen.findByRole("region", { name: "Selected version" });
  const discussion = await screen.findByRole("region", { name: "Discussion" });
  expect(
    selectedVersion.compareDocumentPosition(discussion) & Node.DOCUMENT_POSITION_FOLLOWING
  ).toBeTruthy();
  expect(within(discussion).getByLabelText("Request revision")).toBeInTheDocument();
  expect(within(discussion).getByText("Thread: Why this pacing?")).toBeInTheDocument();
  expect(within(discussion).getByText("Reply to: turn-1")).toBeInTheDocument();
  expect(within(discussion).getAllByText("Result: result-2").length).toBeGreaterThan(0);
  expect(screen.queryByRole("heading", { name: "Composer" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Selected version" })).toBeInTheDocument();
  expect(screen.getByText("Selected result: result-2")).toBeInTheDocument();
  expect(screen.getByText("Selected iteration: iter-2")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Download video" })).toHaveAttribute(
    "href",
    "/api/tasks/task-2/artifacts/final_video.mp4"
  );
  expect(screen.getByRole("link", { name: "Download script" })).toHaveAttribute(
    "href",
    "/api/tasks/task-2/artifacts/current_script.py"
  );
  expect(screen.getByRole("link", { name: "Download validation report" })).toHaveAttribute(
    "href",
    "/api/tasks/task-2/artifacts/validations/validation_report_v1.json"
  );
  expect(screen.getByRole("button", { name: "Show process details" })).toBeInTheDocument();
  expect(screen.queryByText("How This Video Got Here")).not.toBeInTheDocument();
  expect(screen.queryByText("Participants")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Show process details" }));

  expect(screen.getByText("Selected result with current focus")).toBeInTheDocument();
  expect(
    screen.getAllByText("Slow the opener and make the title entrance more deliberate.").length
  ).toBeGreaterThan(0);
  expect(screen.getAllByText("Repairer").length).toBeGreaterThan(0);
  expect(
    screen.getAllByText(
      "This is the latest selected revision for the active iteration and remains aligned with the owner goal."
    ).length
  ).toBeGreaterThan(1);
  expect(screen.getAllByText("Why this version is selected").length).toBeGreaterThan(1);
  expect(screen.getAllByText("Latest visible explanation").length).toBeGreaterThan(1);
  expect(screen.getByText("Who Shaped This Version")).toBeInTheDocument();
  expect(
    screen.getByText(
      "Repairer is the latest visible agent shaping the selected cut for this iteration."
    )
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Decision Notes" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Artifact Lineage" })).toBeInTheDocument();
  expect(screen.getByText("result-1 -> result-2")).toBeInTheDocument();
  expect(screen.getByText("Trigger: Owner requested revision")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Rationale Snapshots" })).toBeInTheDocument();
  expect(screen.getByText("Why the current revision is selected")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Iteration Compare" })).toBeInTheDocument();
  expect(screen.getAllByText("Selected cut with a slower title entrance.").length).toBeGreaterThan(
    0
  );
  expect(
    screen.getByText(
      "The previous cut established the baseline circle motion. The current revision shifts toward a more deliberate title entrance because the owner asked to slow the opener."
    )
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "Participant continuity changed from Planner to Repairer between the compared iterations."
    )
  ).toBeInTheDocument();
  expect(screen.getByText("Recommended next move")).toBeInTheDocument();
  expect(screen.getByText("Production Journal")).toBeInTheDocument();
  expect(screen.getByText("Selected result recorded")).toBeInTheDocument();
  expect(
    screen.getByText(
      "Continue 'Why this pacing?' with Repairer while staying on the active iteration."
    )
  ).toBeInTheDocument();
  expect(screen.getAllByText("Why this pacing?").length).toBeGreaterThan(1);
  expect(screen.getByText("Continuity: iteration")).toBeInTheDocument();
  expect(screen.getByText("Reply policy: continue_thread")).toBeInTheDocument();
  expect(screen.getByText("Participant Runtime")).toBeInTheDocument();
  expect(
    screen.getByText(
      "Repairer is currently expected to respond, while Planner also shaped the active iteration."
    )
  ).toBeInTheDocument();
  expect(screen.getByText("Continuity mode: keep_current_participant")).toBeInTheDocument();
  expect(screen.getByText("Locked target: yes")).toBeInTheDocument();
  expect(screen.getByText("Iteration Detail")).toBeInTheDocument();
  await waitFor(() => {
    expect(
      screen.getByText("This revision carries the slower opener and the selected title entrance.")
    ).toBeInTheDocument();
  });
  expect(screen.getByText("Focus result: result-2")).toBeInTheDocument();
  expect(screen.getByText("How This Video Got Here")).toBeInTheDocument();
  expect(screen.getByText("answered")).toBeInTheDocument();
  expect(screen.getByText("Repairer is refining this cut")).toBeInTheDocument();
  expect(screen.getByText("primary emphasis")).toBeInTheDocument();
  expect(screen.getAllByText(/Intent:/).length).toBeGreaterThan(1);
  expect(screen.getAllByText("Intent: request_explanation").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Replies to: turn-1").length).toBeGreaterThan(0);
  expect(
    screen.getByText(
      "Review the latest selected result, then request a focused revision or record a note."
    )
  ).toBeInTheDocument();
  expect(screen.getByText("Participants")).toBeInTheDocument();
  expect(screen.getByText("Owner participant controls")).toBeInTheDocument();
  expect(
    screen.getByText("Invite reviewers or helper agents into this thread.")
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Invite participant" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Request revision" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Ask why" })).toBeInTheDocument();
  expect(
    screen.getByText("Create the next revision from the selected result and current goal.")
  ).toBeInTheDocument();
  expect(
    screen.getByText("The selected cut is ready for review or a focused revision request.")
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "New messages will attach to iter-2, stay anchored to result-2, and hand off to Repairer."
    )
  ).toBeInTheDocument();
  expect(within(discussion).getAllByText("Reply target: Repairer").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /draw a circle/ }));
  await waitFor(() => {
    expect(
      screen.getByText("This is the origin iteration that established the brisk opener.")
    ).toBeInTheDocument();
  });
  expect(screen.getByText("Focus result: result-1")).toBeInTheDocument();
  expect(
    screen.getByText(
      "New messages will attach to iter-1, stay anchored to result-1, and hand off to Planner."
    )
  ).toBeInTheDocument();
  expect(within(discussion).getAllByText("Reply target: Planner").length).toBeGreaterThan(0);
});

test("video thread page invites and removes participants from the owner panel", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requests: Array<{ method: string; path: string; body?: string | null }> = [];
  let surfaceIndex = 0;
  const surfaces = [
    {
      thread_header: {
        thread_id: "thread-1",
        title: "Circle explainer",
        status: "active",
        current_iteration_id: "iter-2",
        selected_result_id: "result-2",
      },
      thread_summary: "A durable collaboration thread for iterating on this video.",
      current_focus: {
        current_iteration_id: "iter-2",
        current_iteration_goal: "Slow the opener and make the title entrance more deliberate.",
        current_result_id: "result-2",
        current_result_summary: "Selected cut with a slower title entrance.",
      },
      selection_summary: {
        title: "Why this version is selected",
        summary:
          "The latest revision stays aligned with the owner goal and keeps the slower title entrance.",
        selected_result_id: "result-2",
        author_display_name: "Repairer",
        author_role: "repairer",
      },
      latest_explanation: {
        title: "Latest visible explanation",
        summary: "The current version favors the slower title entrance.",
        turn_id: "turn-2",
        speaker_display_name: "Repairer",
        speaker_role: "repairer",
      },
      authorship: {
        title: "Who shaped this version",
        summary: "Repairer is the latest visible agent shaping this iteration.",
        primary_agent_display_name: "Repairer",
        primary_agent_role: "repairer",
        source_iteration_id: "iter-2",
        source_run_id: null,
        source_turn_id: "turn-2",
      },
      decision_notes: { title: "Decision Notes", items: [] },
      next_recommended_move: {
        title: "Recommended next move",
        summary:
          "Review the latest selected result, then request a focused revision or record a note.",
        recommended_action_id: "request_revision",
        recommended_action_label: "Request revision",
        owner_action_required: "review_latest_result",
        tone: "attention",
      },
      responsibility: {
        owner_action_required: "review_latest_result",
      },
      iteration_workbench: {
        selected_iteration_id: "iter-2",
        latest_iteration_id: "iter-2",
        iterations: [
          {
            iteration_id: "iter-2",
            title: "Slow the opener",
            goal: "Slow the opener and make the title entrance more deliberate.",
            status: "active",
            resolution_state: "open",
            requested_action: "revise",
          },
        ],
      },
      conversation: { turns: [] },
      history: { cards: [] },
      production_journal: { title: "Production Journal", summary: "", entries: [] },
      discussion_groups: { groups: [] },
      process: { runs: [] },
      participants: {
        items: [
          {
            participant_id: "owner",
            participant_type: "owner",
            role: "owner",
            display_name: "Owner",
            agent_id: "agent-a",
          },
        ],
        management: {
          can_manage: true,
          can_invite: true,
          can_remove: true,
          invite_label: "Invite participant",
          invite_placeholder: "Agent id",
          default_role: "reviewer",
          default_capabilities: ["review_bundle:read"],
          remove_label: "Remove participant",
          removable_participant_ids: [],
          disabled_reason: "",
          context_hint: "Invite reviewers or helper agents into this thread.",
        },
      },
      actions: { items: [] },
      composer: {
        placeholder: "Ask why this version was made or request the next change.",
        submit_label: "Send",
        disabled: false,
        context_hint: "",
      },
      render_contract: {
        default_focus_panel: "next_recommended_move",
        panel_tone: "active",
        display_priority: "normal",
        badge_order: ["owner_action_required"],
        panel_order: [
          "next_recommended_move",
          "decision_notes",
          "production_journal",
          "history",
          "participants",
          "composer",
        ],
        default_expanded_panels: [
          "next_recommended_move",
          "decision_notes",
          "production_journal",
          "history",
          "participants",
        ],
        sticky_primary_action_emphasis: "normal",
        panel_presentations: [
          {
            panel_id: "next_recommended_move",
            tone: "attention",
            emphasis: "primary",
            default_open: true,
            collapsible: false,
          },
          {
            panel_id: "decision_notes",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
          {
            panel_id: "production_journal",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
          {
            panel_id: "history",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
        ],
        sticky_primary_action_id: null,
      },
    },
    {
      thread_header: {
        thread_id: "thread-1",
        title: "Circle explainer",
        status: "active",
        current_iteration_id: "iter-2",
        selected_result_id: "result-2",
      },
      thread_summary: "A durable collaboration thread for iterating on this video.",
      current_focus: {
        current_iteration_id: "iter-2",
        current_iteration_goal: "Slow the opener and make the title entrance more deliberate.",
        current_result_id: "result-2",
        current_result_summary: "Selected cut with a slower title entrance.",
      },
      selection_summary: {
        title: "Why this version is selected",
        summary:
          "The latest revision stays aligned with the owner goal and keeps the slower title entrance.",
        selected_result_id: "result-2",
        author_display_name: "Repairer",
        author_role: "repairer",
      },
      latest_explanation: {
        title: "Latest visible explanation",
        summary: "The current version favors the slower title entrance.",
        turn_id: "turn-2",
        speaker_display_name: "Repairer",
        speaker_role: "repairer",
      },
      authorship: {
        title: "Who shaped this version",
        summary: "Repairer is the latest visible agent shaping this iteration.",
        primary_agent_display_name: "Repairer",
        primary_agent_role: "repairer",
        source_iteration_id: "iter-2",
        source_run_id: null,
        source_turn_id: "turn-2",
      },
      decision_notes: { title: "Decision Notes", items: [] },
      next_recommended_move: {
        title: "Recommended next move",
        summary:
          "Review the latest selected result, then request a focused revision or record a note.",
        recommended_action_id: "request_revision",
        recommended_action_label: "Request revision",
        owner_action_required: "review_latest_result",
        tone: "attention",
      },
      responsibility: {
        owner_action_required: "review_latest_result",
      },
      iteration_workbench: {
        selected_iteration_id: "iter-2",
        latest_iteration_id: "iter-2",
        iterations: [
          {
            iteration_id: "iter-2",
            title: "Slow the opener",
            goal: "Slow the opener and make the title entrance more deliberate.",
            status: "active",
            resolution_state: "open",
            requested_action: "revise",
          },
        ],
      },
      conversation: { turns: [] },
      history: { cards: [] },
      production_journal: { title: "Production Journal", summary: "", entries: [] },
      discussion_groups: { groups: [] },
      process: { runs: [] },
      participants: {
        items: [
          {
            participant_id: "owner",
            participant_type: "owner",
            role: "owner",
            display_name: "Owner",
            agent_id: "agent-a",
          },
          {
            participant_id: "reviewer-1",
            participant_type: "agent",
            role: "reviewer",
            display_name: "Reviewer",
            agent_id: "reviewer-1",
          },
        ],
        management: {
          can_manage: true,
          can_invite: true,
          can_remove: true,
          invite_label: "Invite participant",
          invite_placeholder: "Agent id",
          default_role: "reviewer",
          default_capabilities: ["review_bundle:read"],
          remove_label: "Remove participant",
          removable_participant_ids: ["reviewer-1"],
          disabled_reason: "",
          context_hint: "Invite reviewers or helper agents into this thread.",
        },
      },
      actions: { items: [] },
      composer: {
        placeholder: "Ask why this version was made or request the next change.",
        submit_label: "Send",
        disabled: false,
        context_hint: "",
      },
      render_contract: {
        default_focus_panel: "next_recommended_move",
        panel_tone: "active",
        display_priority: "normal",
        badge_order: ["owner_action_required"],
        panel_order: [
          "next_recommended_move",
          "decision_notes",
          "production_journal",
          "history",
          "participants",
          "composer",
        ],
        default_expanded_panels: [
          "next_recommended_move",
          "decision_notes",
          "production_journal",
          "history",
          "participants",
        ],
        sticky_primary_action_emphasis: "normal",
        panel_presentations: [
          {
            panel_id: "next_recommended_move",
            tone: "attention",
            emphasis: "primary",
            default_open: true,
            collapsible: false,
          },
          {
            panel_id: "decision_notes",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
          {
            panel_id: "production_journal",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
          {
            panel_id: "history",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
        ],
        sticky_primary_action_id: null,
      },
    },
    {
      thread_header: {
        thread_id: "thread-1",
        title: "Circle explainer",
        status: "active",
        current_iteration_id: "iter-2",
        selected_result_id: "result-2",
      },
      thread_summary: "A durable collaboration thread for iterating on this video.",
      current_focus: {
        current_iteration_id: "iter-2",
        current_iteration_goal: "Slow the opener and make the title entrance more deliberate.",
        current_result_id: "result-2",
        current_result_summary: "Selected cut with a slower title entrance.",
      },
      selection_summary: {
        title: "Why this version is selected",
        summary:
          "The latest revision stays aligned with the owner goal and keeps the slower title entrance.",
        selected_result_id: "result-2",
        author_display_name: "Repairer",
        author_role: "repairer",
      },
      latest_explanation: {
        title: "Latest visible explanation",
        summary: "The current version favors the slower title entrance.",
        turn_id: "turn-2",
        speaker_display_name: "Repairer",
        speaker_role: "repairer",
      },
      authorship: {
        title: "Who shaped this version",
        summary: "Repairer is the latest visible agent shaping this iteration.",
        primary_agent_display_name: "Repairer",
        primary_agent_role: "repairer",
        source_iteration_id: "iter-2",
        source_run_id: null,
        source_turn_id: "turn-2",
      },
      decision_notes: { title: "Decision Notes", items: [] },
      next_recommended_move: {
        title: "Recommended next move",
        summary:
          "Review the latest selected result, then request a focused revision or record a note.",
        recommended_action_id: "request_revision",
        recommended_action_label: "Request revision",
        owner_action_required: "review_latest_result",
        tone: "attention",
      },
      responsibility: {
        owner_action_required: "review_latest_result",
      },
      iteration_workbench: {
        selected_iteration_id: "iter-2",
        latest_iteration_id: "iter-2",
        iterations: [
          {
            iteration_id: "iter-2",
            title: "Slow the opener",
            goal: "Slow the opener and make the title entrance more deliberate.",
            status: "active",
            resolution_state: "open",
            requested_action: "revise",
          },
        ],
      },
      conversation: { turns: [] },
      history: { cards: [] },
      production_journal: { title: "Production Journal", summary: "", entries: [] },
      discussion_groups: { groups: [] },
      process: { runs: [] },
      participants: {
        items: [
          {
            participant_id: "owner",
            participant_type: "owner",
            role: "owner",
            display_name: "Owner",
            agent_id: "agent-a",
          },
        ],
        management: {
          can_manage: true,
          can_invite: true,
          can_remove: true,
          invite_label: "Invite participant",
          invite_placeholder: "Agent id",
          default_role: "reviewer",
          default_capabilities: ["review_bundle:read"],
          remove_label: "Remove participant",
          removable_participant_ids: [],
          disabled_reason: "",
          context_hint: "Invite reviewers or helper agents into this thread.",
        },
      },
      actions: { items: [] },
      composer: {
        placeholder: "Ask why this version was made or request the next change.",
        submit_label: "Send",
        disabled: false,
        context_hint: "",
      },
      render_contract: {
        default_focus_panel: "next_recommended_move",
        panel_tone: "active",
        display_priority: "normal",
        badge_order: ["owner_action_required"],
        panel_order: [
          "next_recommended_move",
          "decision_notes",
          "production_journal",
          "history",
          "participants",
          "composer",
        ],
        default_expanded_panels: [
          "next_recommended_move",
          "decision_notes",
          "production_journal",
          "history",
          "participants",
        ],
        sticky_primary_action_emphasis: "normal",
        panel_presentations: [
          {
            panel_id: "next_recommended_move",
            tone: "attention",
            emphasis: "primary",
            default_open: true,
            collapsible: false,
          },
          {
            panel_id: "decision_notes",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
          {
            panel_id: "production_journal",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
          {
            panel_id: "history",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
        ],
        sticky_primary_action_id: null,
      },
    },
  ];

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requests.push({
      path,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });

    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = surfaces[Math.min(surfaceIndex, surfaces.length - 1)];
      surfaceIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (path === "/api/video-threads/thread-1/participants" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          thread_id: "thread-1",
          participant: {
            participant_id: "reviewer-1",
            participant_type: "agent",
            role: "reviewer",
            display_name: "Reviewer",
            agent_id: "reviewer-1",
          },
          removed: false,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    if (
      path === "/api/video-threads/thread-1/participants/reviewer-1" &&
      init?.method === "DELETE"
    ) {
      return new Response(JSON.stringify({ thread_id: "thread-1", removed: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/videos/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/videos/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Circle explainer" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show process details" }));

  await user.type(screen.getByLabelText("Participant agent id"), "reviewer-1");
  await user.type(screen.getByLabelText("Participant display name"), "Reviewer");
  await user.click(screen.getByRole("button", { name: "Invite participant" }));

  await waitFor(() => {
    expect(screen.getAllByText("Reviewer").length).toBeGreaterThan(0);
  });
  expect(
    requests.some(
      (request) =>
        request.method === "POST" &&
        request.path === "/api/video-threads/thread-1/participants" &&
        request.body?.includes('"participant_id":"reviewer-1"') &&
        request.body?.includes('"display_name":"Reviewer"')
    )
  ).toBe(true);

  await user.click(screen.getByRole("button", { name: "Remove participant Reviewer" }));

  await waitFor(() => {
    expect(
      screen.queryByRole("button", { name: "Remove participant Reviewer" })
    ).not.toBeInTheDocument();
  });
  expect(
    requests.some(
      (request) =>
        request.method === "DELETE" &&
        request.path === "/api/video-threads/thread-1/participants/reviewer-1"
    )
  ).toBe(true);
});

test("video thread page routes discussion actions through the selected composer mode", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requests: Array<{ method: string; path: string; body?: string | null }> = [];

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requests.push({
      path,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });

    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(
        JSON.stringify({
          thread_header: {
            thread_id: "thread-1",
            title: "Circle explainer",
            status: "active",
            current_iteration_id: "iter-1",
            selected_result_id: "result-1",
          },
          thread_summary: "A durable collaboration thread for iterating on this video.",
          current_focus: {
            current_iteration_id: "iter-1",
            current_iteration_goal: "Slow the opener a little.",
            current_result_id: "result-1",
            current_result_summary: "Selected cut with a slower title entrance.",
          },
          selection_summary: {
            title: "Why this version is selected",
            summary: "The current cut remains the preferred version.",
            selected_result_id: "result-1",
          },
          latest_explanation: {
            title: "Latest visible explanation",
            summary: "The slower opener gives the title room to land.",
            turn_id: "turn-2",
            speaker_display_name: "Repairer",
            speaker_role: "repairer",
          },
          authorship: {
            title: "Who shaped this version",
            summary: "Repairer shaped the latest selected cut.",
            primary_agent_display_name: "Repairer",
            primary_agent_role: "repairer",
            source_iteration_id: "iter-1",
            source_turn_id: "turn-2",
          },
          decision_notes: { title: "Decision Notes", items: [] },
          artifact_lineage: {
            title: "Artifact Lineage",
            summary: "",
            selected_result_id: "result-1",
            items: [],
          },
          rationale_snapshots: {
            title: "Rationale Snapshots",
            summary: "",
            current_iteration_id: "iter-1",
            items: [],
          },
          next_recommended_move: {
            title: "Recommended next move",
            summary: "Record focused feedback for the shaping agent.",
            recommended_action_id: "discuss",
            recommended_action_label: "Add note",
            owner_action_required: "share_feedback",
            tone: "active",
          },
          responsibility: {
            owner_action_required: "share_feedback",
            expected_agent_role: "repairer",
            expected_agent_id: "repairer-1",
          },
          iteration_workbench: {
            selected_iteration_id: "iter-1",
            latest_iteration_id: "iter-1",
            iterations: [
              {
                iteration_id: "iter-1",
                title: "Slow the opener",
                goal: "Slow the opener a little.",
                status: "active",
                resolution_state: "open",
                requested_action: "revise",
                result_summary: "Selected cut with a slower title entrance.",
                responsible_role: "repairer",
                responsible_agent_id: "repairer-1",
              },
            ],
          },
          iteration_detail: {
            title: "Iteration Detail",
            summary: "This iteration currently tracks one visible turn, no runs, and one result.",
            selected_iteration_id: "iter-1",
            resource_uri: "video-thread://thread-1/iterations/iter-1.json",
            turn_count: 1,
            run_count: 0,
            result_count: 1,
          },
          conversation: { turns: [] },
          history: { cards: [] },
          production_journal: { title: "Production Journal", summary: "", entries: [] },
          discussion_groups: { groups: [] },
          process: { runs: [] },
          participants: {
            items: [
              {
                participant_id: "owner",
                participant_type: "owner",
                role: "owner",
                display_name: "Owner",
                agent_id: "agent-a",
              },
              {
                participant_id: "repairer-1",
                participant_type: "agent",
                role: "repairer",
                display_name: "Repairer",
                agent_id: "repairer-1",
              },
            ],
            management: {
              can_manage: true,
              can_invite: true,
              can_remove: true,
              invite_label: "Invite participant",
              invite_placeholder: "Agent id",
              default_role: "reviewer",
              default_capabilities: ["review_bundle:read"],
              remove_label: "Remove participant",
              removable_participant_ids: ["repairer-1"],
              disabled_reason: "",
              context_hint: "Invite reviewers or helper agents into this thread.",
            },
          },
          actions: {
            items: [
              {
                action_id: "request_revision",
                label: "Request revision",
                description: "Create the next revision from the selected result and current goal.",
                tone: "strong",
                disabled: false,
                disabled_reason: "",
              },
              {
                action_id: "request_explanation",
                label: "Ask why",
                description: "Request a product-safe explanation for the current direction.",
                tone: "neutral",
                disabled: false,
                disabled_reason: "",
              },
              {
                action_id: "discuss",
                label: "Add note",
                description: "Record feedback for the current shaping agent.",
                tone: "muted",
                disabled: false,
                disabled_reason: "",
              },
            ],
          },
          composer: {
            placeholder: "Ask why this version was made or request the next change.",
            submit_label: "Send",
            disabled: false,
            disabled_reason: "",
            context_hint: "The selected cut is ready for focused follow-up.",
            target: {
              iteration_id: "iter-1",
              result_id: "result-1",
              addressed_participant_id: "repairer-1",
              addressed_agent_id: "repairer-1",
              addressed_display_name: "Repairer",
              agent_role: "repairer",
              agent_display_name: "Repairer",
              summary:
                "New messages will attach to iter-1, stay anchored to result-1, and hand off to Repairer.",
            },
          },
          render_contract: {
            default_focus_panel: "composer",
            panel_tone: "active",
            display_priority: "normal",
            badge_order: ["owner_action_required"],
            panel_order: ["composer"],
            default_expanded_panels: ["composer"],
            sticky_primary_action_id: "discuss",
            sticky_primary_action_emphasis: "normal",
            panel_presentations: [
              {
                panel_id: "composer",
                tone: "accent",
                emphasis: "primary",
                default_open: true,
                collapsible: false,
              },
            ],
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(
        JSON.stringify({
          thread_id: "thread-1",
          iteration_id: "iter-1",
          title: "Iteration Detail",
          summary: "This iteration carries the latest owner feedback and selected result.",
          execution_summary: {
            title: "Execution Summary",
            summary:
              "Repairer is currently repairing for task task-1 while shaping result result-1.",
            task_id: "task-1",
            run_id: "thread-run:task-1",
            status: "running",
            phase: "repairing",
            agent_id: "repairer-1",
            agent_display_name: "Repairer",
            agent_role: "repairer",
            result_id: "result-1",
            discussion_group_id: "group-turn-1",
            reply_to_turn_id: "turn-1",
            latest_owner_turn_id: "turn-1",
            latest_agent_turn_id: "turn-2",
            is_active: true,
          },
          composer_target: {
            iteration_id: "iter-1",
            result_id: "result-1",
            addressed_participant_id: "repairer-1",
            addressed_agent_id: "repairer-1",
            addressed_display_name: "Repairer",
            agent_role: "repairer",
            agent_display_name: "Repairer",
            summary:
              "New messages will attach to iter-1, stay anchored to result-1, and hand off to Repairer.",
          },
          iteration: {
            iteration_id: "iter-1",
            thread_id: "thread-1",
            goal: "Slow the opener a little.",
            requested_action: "revise",
            preserve_working_parts: true,
            status: "active",
            resolution_state: "open",
            selected_result_id: "result-1",
            source_result_id: null,
            responsible_role: "repairer",
            responsible_agent_id: "repairer-1",
          },
          turns: [],
          runs: [],
          results: [
            {
              result_id: "result-1",
              status: "ready",
              result_summary: "Selected cut with a slower title entrance.",
              selected: true,
              video_resource: "video-task://task-1/artifacts/final.mp4",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    if (path === "/api/video-threads/thread-1/turns" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          thread: {
            thread_id: "thread-1",
          },
          iteration: {
            iteration_id: "iter-1",
          },
          turn: {
            turn_id: "turn-9",
            turn_type: "owner_request",
            intent_type: "discuss",
            addressed_participant_id: "repairer-1",
            addressed_agent_id: "repairer-1",
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1/request-revision" &&
      init?.method === "POST"
    ) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1/request-explanation" &&
      init?.method === "POST"
    ) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/videos/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/videos/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Circle explainer" })).toBeInTheDocument();
  const discussion = await screen.findByRole("region", { name: "Discussion" });
  expect(within(discussion).getByLabelText("Request revision")).toBeInTheDocument();
  expect(within(discussion).getByText("Reply to: turn-1")).toBeInTheDocument();
  expect(within(discussion).getByText("Result: result-1")).toBeInTheDocument();

  await user.type(
    within(discussion).getByLabelText("Request revision"),
    "Please keep this pacing but make the title land softer."
  );
  await user.click(within(discussion).getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/iterations/iter-1/request-revision" &&
          request.body?.includes(
            '"summary":"Please keep this pacing but make the title land softer."'
          )
      )
    ).toBe(true);
  });

  await user.click(within(discussion).getByRole("button", { name: "Ask why" }));
  await user.type(
    within(discussion).getByLabelText("Ask why"),
    "Why does the current title entrance feel more deliberate?"
  );
  await user.click(within(discussion).getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/iterations/iter-1/request-explanation" &&
          request.body?.includes(
            '"summary":"Why does the current title entrance feel more deliberate?"'
          )
      )
    ).toBe(true);
  });

  await user.click(within(discussion).getByRole("button", { name: "Add note" }));
  await user.type(
    within(discussion).getByLabelText("Add note"),
    "Please keep this pacing but make the title land softer."
  );
  await user.click(within(discussion).getByRole("button", { name: "Send" }));
  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/turns" &&
          request.body?.includes('"addressed_participant_id":"repairer-1"') &&
          request.body?.includes('"reply_to_turn_id":"turn-1"') &&
          request.body?.includes('"related_result_id":"result-1"')
      )
    ).toBe(true);
  });
});

test("video thread page follows the refreshed iteration after requesting a revision", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requests: Array<{ method: string; path: string; body?: string | null }> = [];
  const surfaces = [
    createThreadSurface(),
    createThreadSurface({
      thread_header: {
        current_iteration_id: "iter-2",
        selected_result_id: "result-2",
      },
      current_focus: {
        current_iteration_id: "iter-2",
        current_iteration_goal: "Keep the pacing but soften the landing.",
        current_result_id: "result-2",
        current_result_summary: "A softer title landing is now selected.",
        current_result_author_display_name: "Finisher",
        current_result_author_role: "finisher",
        current_result_selection_reason: "The new revision now carries the thread forward.",
      },
      selection_summary: {
        selected_result_id: "result-2",
        summary: "The new revision now carries the thread forward.",
        author_display_name: "Finisher",
        author_role: "finisher",
      },
      latest_explanation: {
        summary: "The landing was softened without losing the clearer opener.",
        turn_id: "turn-10",
        speaker_display_name: "Finisher",
        speaker_role: "finisher",
      },
      authorship: {
        summary: "Finisher shaped the newly selected revision.",
        primary_agent_display_name: "Finisher",
        primary_agent_role: "finisher",
        source_iteration_id: "iter-2",
        source_turn_id: "turn-10",
      },
      iteration_compare: {
        previous_iteration_id: "iter-1",
        current_iteration_id: "iter-2",
        previous_result_id: "result-1",
        current_result_id: "result-2",
        change_summary: "The current revision softens the title landing.",
        rationale_shift_summary:
          "The owner asked to preserve the pacing while easing the final title beat.",
        continuity_status: "changed",
        continuity_summary: "The iteration focus moved from Repairer to Finisher.",
      },
      next_recommended_move: {
        recommended_action_id: "discuss",
        recommended_action_label: "Add note",
        summary: "Review the new revision before deciding on another pass.",
      },
      responsibility: {
        owner_action_required: "review_latest_result",
        expected_agent_role: "finisher",
        expected_agent_id: "finisher-1",
      },
      iteration_workbench: {
        selected_iteration_id: "iter-2",
        latest_iteration_id: "iter-2",
        iterations: [
          {
            iteration_id: "iter-1",
            title: "Slow the opener",
            goal: "Slow the opener a little.",
            status: "closed",
            resolution_state: "resolved",
            requested_action: "revise",
            result_summary: "Selected cut with a slower title entrance.",
            responsible_role: "repairer",
            responsible_agent_id: "repairer-1",
          },
          {
            iteration_id: "iter-2",
            title: "Soften the title landing",
            goal: "Keep the pacing but soften the landing.",
            status: "active",
            resolution_state: "open",
            requested_action: "revise",
            result_summary: "A softer title landing is now selected.",
            responsible_role: "finisher",
            responsible_agent_id: "finisher-1",
          },
        ],
      },
      iteration_detail: {
        summary: "The newest revision is now the selected process focus.",
        selected_iteration_id: "iter-2",
        resource_uri: "video-thread://thread-1/iterations/iter-2.json",
        turn_count: 1,
        run_count: 1,
        result_count: 1,
      },
      discussion_runtime: {
        active_iteration_id: "iter-2",
        default_reply_to_turn_id: "turn-9",
        default_related_result_id: "result-2",
        addressed_participant_id: "finisher-1",
        addressed_agent_id: "finisher-1",
        addressed_display_name: "Finisher",
        active_thread_title: "Revision handoff",
        active_thread_summary: "The new revision is ready for follow-up.",
      },
      participant_runtime: {
        active_iteration_id: "iter-2",
        expected_participant_id: "finisher-1",
        expected_agent_id: "finisher-1",
        expected_display_name: "Finisher",
        expected_role: "finisher",
      },
      process: {
        runs: [{ run_id: "run-2", iteration_id: "iter-2", task_id: "task-2" }],
      },
      participants: {
        items: [
          {
            participant_id: "owner",
            participant_type: "owner",
            role: "owner",
            display_name: "Owner",
            agent_id: "agent-a",
          },
          {
            participant_id: "finisher-1",
            participant_type: "agent",
            role: "finisher",
            display_name: "Finisher",
            agent_id: "finisher-1",
          },
        ],
        management: {
          removable_participant_ids: ["finisher-1"],
        },
      },
      composer: {
        target: {
          iteration_id: "iter-2",
          result_id: "result-2",
          addressed_participant_id: "finisher-1",
          addressed_agent_id: "finisher-1",
          addressed_display_name: "Finisher",
          agent_role: "finisher",
          agent_display_name: "Finisher",
          summary:
            "New messages will attach to iter-2, stay anchored to result-2, and hand off to Finisher.",
        },
      },
    }),
  ];
  let surfaceIndex = 0;

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requests.push({
      path,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });

    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = surfaces[Math.min(surfaceIndex, surfaces.length - 1)];
      surfaceIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(JSON.stringify(createIterationDetail()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-2" &&
      (!init?.method || init.method === "GET")
    ) {
      return new Response(
        JSON.stringify(
          createIterationDetail({
            iteration_id: "iter-2",
            summary: "Revision request opened iter-2 and shifted the live detail focus.",
            execution_summary: {
              summary: "Finisher is now shaping result result-2 for task task-2.",
              task_id: "task-2",
              run_id: "thread-run:task-2",
              status: "running",
              phase: "planning",
              agent_id: "finisher-1",
              agent_display_name: "Finisher",
              agent_role: "finisher",
              result_id: "result-2",
              reply_to_turn_id: "turn-9",
              latest_owner_turn_id: "turn-9",
              latest_agent_turn_id: "turn-10",
            },
            composer_target: {
              iteration_id: "iter-2",
              result_id: "result-2",
              addressed_participant_id: "finisher-1",
              addressed_agent_id: "finisher-1",
              addressed_display_name: "Finisher",
              agent_role: "finisher",
              agent_display_name: "Finisher",
              summary:
                "New messages will attach to iter-2, stay anchored to result-2, and hand off to Finisher.",
            },
            iteration: {
              iteration_id: "iter-2",
              goal: "Keep the pacing but soften the landing.",
              selected_result_id: "result-2",
              source_result_id: "result-1",
              responsible_role: "finisher",
              responsible_agent_id: "finisher-1",
            },
            runs: [
              {
                run_id: "run-2",
                agent_id: "finisher-1",
                agent_display_name: "Finisher",
                role: "finisher",
                status: "running",
                phase: "planning",
                output_summary: "Preparing a softer title landing.",
                task_id: "task-2",
              },
            ],
            results: [
              {
                result_id: "result-2",
                status: "ready",
                result_summary: "A softer title landing is now selected.",
                selected: true,
                video_resource: "video-task://task-2/artifacts/final.mp4",
              },
            ],
          })
        ),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        }
      );
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1/request-revision" &&
      init?.method === "POST"
    ) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/videos/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/videos/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Circle explainer" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show process details" }));
  expect(await screen.findByText("Initial iteration detail.")).toBeInTheDocument();

  const discussion = screen.getByRole("region", { name: "Discussion" });
  await user.type(
    within(discussion).getByLabelText("Request revision"),
    "Please soften the title landing."
  );
  await user.click(within(discussion).getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/iterations/iter-1/request-revision" &&
          request.body?.includes('"summary":"Please soften the title landing."')
      )
    ).toBe(true);
  });

  await waitFor(() => {
    expect(
      screen.getByText("Revision request opened iter-2 and shifted the live detail focus.")
    ).toBeInTheDocument();
  });
  expect(
    screen.getByText("Finisher is now shaping result result-2 for task task-2.")
  ).toBeInTheDocument();
  expect(within(discussion).getByText("Reply to: turn-9")).toBeInTheDocument();
  expect(within(discussion).getByText("Result: result-2")).toBeInTheDocument();
  expect(within(discussion).getAllByText("Reply target: Finisher").length).toBeGreaterThan(0);
  expect(
    within(discussion).getByText(
      "New messages will attach to iter-2, stay anchored to result-2, and hand off to Finisher."
    )
  ).toBeInTheDocument();
  expect(screen.getByText("Selected result: result-2")).toBeInTheDocument();
});

test("video thread page refreshes the inspected iteration detail after adding a discussion note", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requests: Array<{ method: string; path: string; body?: string | null }> = [];
  const surfaces = [
    createThreadSurface(),
    createThreadSurface({
      current_focus: {
        current_iteration_id: "iter-1",
        current_result_id: "result-1",
        current_result_summary:
          "Selected cut with a slower title entrance and recorded owner follow-up.",
      },
      latest_explanation: {
        summary: "The latest note asked for a softer landing while preserving pacing.",
        turn_id: "turn-9",
      },
      iteration_detail: {
        summary: "The selected iteration now includes the newly recorded discussion turn.",
      },
      conversation: {
        turns: [
          {
            turn_id: "turn-9",
            iteration_id: "iter-1",
            title: "Owner note recorded",
            summary: "Please keep the pacing but soften the final title beat.",
            intent_type: "discuss",
            reply_to_turn_id: "turn-1",
            related_result_id: "result-1",
            speaker_type: "owner",
            speaker_role: "owner",
          },
        ],
      },
      discussion_runtime: {
        default_reply_to_turn_id: "turn-9",
        active_thread_summary: "The latest owner note should guide the next response.",
      },
      composer: {
        target: {
          iteration_id: "iter-1",
          result_id: "result-1",
          addressed_participant_id: "repairer-1",
          addressed_agent_id: "repairer-1",
          addressed_display_name: "Repairer",
          agent_role: "repairer",
          agent_display_name: "Repairer",
          summary:
            "The surface refreshed, but the iteration detail must also refresh to show the new owner note.",
        },
      },
    }),
  ];
  const iter1Details = [
    createIterationDetail(),
    createIterationDetail({
      summary: "Updated iteration detail after note.",
      execution_summary: {
        summary: "Repairer is now responding to the latest owner note on result result-1.",
        reply_to_turn_id: "turn-9",
        latest_owner_turn_id: "turn-9",
        latest_agent_turn_id: "turn-10",
      },
      composer_target: {
        summary:
          "New messages will attach to iter-1, stay anchored to result-1, and continue from the new owner note.",
      },
      turns: [
        {
          turn_id: "turn-9",
          title: "Owner note recorded",
          summary: "Please keep the pacing but soften the final title beat.",
          turn_type: "owner_request",
          speaker_display_name: "Owner",
          speaker_role: "owner",
          addressed_display_name: "Repairer",
          addressed_participant_id: "repairer-1",
        },
      ],
    }),
  ];
  let surfaceIndex = 0;
  let iter1DetailIndex = 0;

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requests.push({
      path,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });

    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = surfaces[Math.min(surfaceIndex, surfaces.length - 1)];
      surfaceIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = iter1Details[Math.min(iter1DetailIndex, iter1Details.length - 1)];
      iter1DetailIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (path === "/api/video-threads/thread-1/turns" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          thread: { thread_id: "thread-1" },
          iteration: { iteration_id: "iter-1" },
          turn: {
            turn_id: "turn-9",
            turn_type: "owner_request",
            intent_type: "discuss",
            addressed_participant_id: "repairer-1",
            addressed_agent_id: "repairer-1",
          },
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        }
      );
    }

    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/videos/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/videos/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Circle explainer" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show process details" }));
  expect(await screen.findByText("Initial iteration detail.")).toBeInTheDocument();
  expect(
    screen.getByText(
      "Repairer is currently repairing for task task-1 while shaping result result-1."
    )
  ).toBeInTheDocument();

  const discussion = screen.getByRole("region", { name: "Discussion" });
  await user.click(within(discussion).getByRole("button", { name: "Add note" }));
  await user.type(
    within(discussion).getByLabelText("Add note"),
    "Please keep the pacing but soften the final title beat."
  );
  await user.click(within(discussion).getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/turns" &&
          request.body?.includes(
            '"title":"Please keep the pacing but soften the final title beat."'
          )
      )
    ).toBe(true);
  });

  await waitFor(() => {
    expect(screen.getByText("Updated iteration detail after note.")).toBeInTheDocument();
  });
  expect(
    screen.getByText("Repairer is now responding to the latest owner note on result result-1.")
  ).toBeInTheDocument();
  expect(screen.getAllByText("Owner note recorded").length).toBeGreaterThan(0);
  expect(within(discussion).getByText("Reply to: turn-9")).toBeInTheDocument();
  expect(
    within(discussion).getByText(
      "New messages will attach to iter-1, stay anchored to result-1, and continue from the new owner note."
    )
  ).toBeInTheDocument();
});

test("video thread page refreshes the inspected iteration detail after requesting an explanation", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requests: Array<{ method: string; path: string; body?: string | null }> = [];
  const surfaces = [
    createThreadSurface(),
    createThreadSurface({
      latest_explanation: {
        summary: "The latest explanation clarifies why the slower landing was preferred.",
        turn_id: "turn-11",
        speaker_display_name: "Repairer",
        speaker_role: "repairer",
      },
      iteration_detail: {
        summary: "The selected iteration now includes the refreshed explanation context.",
      },
      conversation: {
        turns: [
          {
            turn_id: "turn-11",
            iteration_id: "iter-1",
            title: "Visible explanation",
            summary: "The slower landing gives the title beat more breathing room.",
            intent_type: "request_explanation",
            reply_to_turn_id: "turn-1",
            related_result_id: "result-1",
            speaker_type: "agent",
            speaker_role: "repairer",
          },
        ],
      },
      discussion_runtime: {
        default_reply_to_turn_id: "turn-11",
        active_thread_summary:
          "The explanation response should stay attached to the selected iteration.",
      },
      composer: {
        target: {
          iteration_id: "iter-1",
          result_id: "result-1",
          addressed_participant_id: "repairer-1",
          addressed_agent_id: "repairer-1",
          addressed_display_name: "Repairer",
          agent_role: "repairer",
          agent_display_name: "Repairer",
          summary: "The refreshed explanation keeps the composer anchored to iter-1 and result-1.",
        },
      },
    }),
  ];
  const iter1Details = [
    createIterationDetail(),
    createIterationDetail({
      summary: "Updated iteration detail after explanation.",
      execution_summary: {
        summary: "Repairer has now answered the explanation request for result result-1.",
        reply_to_turn_id: "turn-11",
        latest_owner_turn_id: "turn-1",
        latest_agent_turn_id: "turn-11",
      },
      composer_target: {
        summary:
          "New messages will attach to iter-1, stay anchored to result-1, and continue from the latest explanation.",
      },
      turns: [
        {
          turn_id: "turn-11",
          title: "Visible explanation",
          summary: "The slower landing gives the title beat more breathing room.",
          turn_type: "agent_reply",
          speaker_display_name: "Repairer",
          speaker_role: "repairer",
          addressed_display_name: "Owner",
          addressed_participant_id: "owner",
        },
      ],
    }),
  ];
  let surfaceIndex = 0;
  let iter1DetailIndex = 0;

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requests.push({
      path,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });

    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = surfaces[Math.min(surfaceIndex, surfaces.length - 1)];
      surfaceIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = iter1Details[Math.min(iter1DetailIndex, iter1Details.length - 1)];
      iter1DetailIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-1/request-explanation" &&
      init?.method === "POST"
    ) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/videos/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/videos/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Circle explainer" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show process details" }));
  expect(await screen.findByText("Initial iteration detail.")).toBeInTheDocument();

  const discussion = screen.getByRole("region", { name: "Discussion" });
  await user.click(within(discussion).getByRole("button", { name: "Ask why" }));
  await user.type(
    within(discussion).getByLabelText("Ask why"),
    "Why does the slower landing feel more deliberate?"
  );
  await user.click(within(discussion).getByRole("button", { name: "Send" }));

  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/iterations/iter-1/request-explanation" &&
          request.body?.includes('"summary":"Why does the slower landing feel more deliberate?"')
      )
    ).toBe(true);
  });

  await waitFor(() => {
    expect(screen.getByText("Updated iteration detail after explanation.")).toBeInTheDocument();
  });
  expect(
    screen.getByText("Repairer has now answered the explanation request for result result-1.")
  ).toBeInTheDocument();
  expect(screen.getAllByText("Visible explanation").length).toBeGreaterThan(0);
  expect(within(discussion).getByText("Reply to: turn-11")).toBeInTheDocument();
  expect(
    within(discussion).getByText(
      "New messages will attach to iter-1, stay anchored to result-1, and continue from the latest explanation."
    )
  ).toBeInTheDocument();
});

test("video thread page shows version cards with select and task actions", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requests: Array<{ method: string; path: string; body?: string | null }> = [];
  let surfaceIndex = 0;
  let iter2DetailIndex = 0;

  const surfaces = [
    {
      thread_header: {
        thread_id: "thread-1",
        title: "Circle explainer",
        status: "active",
        current_iteration_id: "iter-2",
        selected_result_id: "result-2",
      },
      thread_summary: "A durable collaboration thread for iterating on this video.",
      current_focus: {
        current_iteration_id: "iter-2",
        current_iteration_goal: "Slow the opener and make the title entrance more deliberate.",
        current_result_id: "result-2",
        current_result_summary: "Selected cut with a slower title entrance.",
      },
      selection_summary: {
        title: "Why this version is selected",
        summary: "The latest selected version keeps the deliberate title entrance.",
        selected_result_id: "result-2",
      },
      latest_explanation: {
        title: "Latest visible explanation",
        summary: "The slower opener gives the title more room to land.",
      },
      authorship: {
        title: "Who shaped this version",
        summary: "Repairer shaped the latest selected cut.",
        primary_agent_display_name: "Repairer",
        primary_agent_role: "repairer",
      },
      decision_notes: { title: "Decision Notes", items: [] },
      artifact_lineage: {
        title: "Artifact Lineage",
        summary: "",
        selected_result_id: "result-2",
        items: [],
      },
      rationale_snapshots: {
        title: "Rationale Snapshots",
        summary: "",
        current_iteration_id: "iter-2",
        items: [],
      },
      iteration_compare: {
        title: "Iteration Compare",
        summary: "",
        previous_iteration_id: "iter-1",
        current_iteration_id: "iter-2",
        previous_result_id: "result-1",
        current_result_id: surfaceIndex === 0 ? "result-2" : "result-1",
        change_summary: "",
        rationale_shift_summary: "",
        continuity_status: "changed",
        continuity_summary: "",
      },
      next_recommended_move: {
        title: "Recommended next move",
        summary: "Review the current version or switch to another cut.",
        recommended_action_id: "request_revision",
        recommended_action_label: "Request revision",
        owner_action_required: "review_latest_result",
        tone: "attention",
      },
      responsibility: {
        owner_action_required: "review_latest_result",
        expected_agent_role: "repairer",
      },
      iteration_workbench: {
        selected_iteration_id: "iter-2",
        latest_iteration_id: "iter-2",
        iterations: [
          {
            iteration_id: "iter-2",
            title: "Slow the opener",
            goal: "Slow the opener and make the title entrance more deliberate.",
            status: "active",
            resolution_state: "open",
            requested_action: "revise",
            result_summary: "Two visible candidate cuts are available.",
          },
        ],
      },
      iteration_detail: {
        title: "Iteration Detail",
        summary: "Inspect the selected iteration to review visible turns, runs, and results.",
        selected_iteration_id: "iter-2",
        resource_uri: "video-thread://thread-1/iterations/iter-2.json",
        turn_count: 1,
        run_count: 1,
        result_count: 2,
      },
      conversation: { turns: [] },
      history: { cards: [] },
      production_journal: {
        title: "Production Journal",
        summary: "",
        entries: [
          {
            entry_id: "journal-result-2",
            entry_kind: "result",
            title: "Selected result recorded",
            summary: "Selected cut with a slower title entrance.",
            stage: "result",
            status: "ready",
            iteration_id: "iter-2",
            task_id: "task-2",
            run_id: null,
            result_id: "result-2",
            actor_display_name: "Repairer",
            actor_role: "repairer",
            resource_refs: ["video-task://task-2/artifacts/final.mp4"],
          },
        ],
      },
      discussion_groups: { groups: [] },
      discussion_runtime: {
        title: "Discussion Runtime",
        summary: "Discuss the currently selected cut.",
        active_iteration_id: "iter-2",
        active_discussion_group_id: null,
        continuity_scope: "iteration",
        reply_policy: "continue_thread",
        default_intent_type: "discuss",
        default_reply_to_turn_id: "turn-1",
        default_related_result_id: surfaceIndex === 0 ? "result-2" : "result-1",
        addressed_participant_id: "repairer-1",
        addressed_agent_id: "repairer-1",
        addressed_display_name: "Repairer",
        suggested_follow_up_modes: [],
        active_thread_title: "Version review",
        active_thread_summary: "Choose the cut you want to carry forward.",
        latest_owner_turn_id: "turn-1",
        latest_agent_turn_id: null,
        latest_agent_summary: "",
      },
      participant_runtime: {
        title: "Participant Runtime",
        summary: "",
        active_iteration_id: "iter-2",
        expected_participant_id: "repairer-1",
        expected_agent_id: "repairer-1",
        expected_display_name: "Repairer",
        expected_role: "repairer",
        continuity_mode: "keep_current_participant",
        follow_up_target_locked: true,
        recent_contributors: [],
      },
      process: {
        runs: [
          {
            run_id: "run-2",
            iteration_id: "iter-2",
            task_id: "task-2",
            role: "repairer",
            status: "completed",
            phase: "completed",
            output_summary: "Produced two candidate cuts.",
          },
        ],
      },
      participants: {
        items: [
          {
            participant_id: "owner",
            participant_type: "owner",
            role: "owner",
            display_name: "Owner",
          },
        ],
        management: {
          can_manage: true,
          can_invite: true,
          can_remove: true,
          invite_label: "Invite participant",
          invite_placeholder: "Agent id",
          default_role: "reviewer",
          default_capabilities: ["review_bundle:read"],
          remove_label: "Remove participant",
          removable_participant_ids: [],
          disabled_reason: "",
          context_hint: "Invite reviewers or helper agents into this thread.",
        },
      },
      actions: {
        items: [
          {
            action_id: "request_revision",
            label: "Request revision",
            description: "Create the next revision from the selected result and current goal.",
            tone: "strong",
            disabled: false,
          },
        ],
      },
      composer: {
        placeholder: "Ask why this version was made or request the next change.",
        submit_label: "Send",
        disabled: false,
        context_hint: "The selected cut is ready for review or a focused revision request.",
        target: {
          iteration_id: "iter-2",
          result_id: surfaceIndex === 0 ? "result-2" : "result-1",
          addressed_participant_id: "repairer-1",
          addressed_agent_id: "repairer-1",
          addressed_display_name: "Repairer",
          agent_role: "repairer",
          agent_display_name: "Repairer",
          summary:
            surfaceIndex === 0
              ? "New messages will attach to iter-2, stay anchored to result-2, and hand off to Repairer."
              : "New messages will attach to iter-2, stay anchored to result-1, and hand off to Repairer.",
        },
      },
      render_contract: {
        default_focus_panel: "composer",
        panel_tone: "attention",
        display_priority: "normal",
        badge_order: ["owner_action_required"],
        panel_order: ["composer", "iteration_detail"],
        default_expanded_panels: ["composer", "iteration_detail"],
        sticky_primary_action_id: "request_revision",
        sticky_primary_action_emphasis: "strong",
        panel_presentations: [
          {
            panel_id: "iteration_detail",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
        ],
      },
    },
    {
      thread_header: {
        thread_id: "thread-1",
        title: "Circle explainer",
        status: "active",
        current_iteration_id: "iter-2",
        selected_result_id: "result-1",
      },
      thread_summary: "A durable collaboration thread for iterating on this video.",
      current_focus: {
        current_iteration_id: "iter-2",
        current_iteration_goal: "Slow the opener and make the title entrance more deliberate.",
        current_result_id: "result-1",
        current_result_summary: "Earlier cut with a sharper title entrance.",
      },
      selection_summary: {
        title: "Why this version is selected",
        summary: "The owner switched back to compare the earlier cut.",
        selected_result_id: "result-1",
      },
      latest_explanation: {
        title: "Latest visible explanation",
        summary: "The earlier cut lands the title faster.",
      },
      authorship: {
        title: "Who shaped this version",
        summary: "Repairer shaped both visible cuts.",
        primary_agent_display_name: "Repairer",
        primary_agent_role: "repairer",
      },
      decision_notes: { title: "Decision Notes", items: [] },
      artifact_lineage: {
        title: "Artifact Lineage",
        summary: "",
        selected_result_id: "result-1",
        items: [],
      },
      rationale_snapshots: {
        title: "Rationale Snapshots",
        summary: "",
        current_iteration_id: "iter-2",
        items: [],
      },
      iteration_compare: {
        title: "Iteration Compare",
        summary: "",
        previous_iteration_id: "iter-1",
        current_iteration_id: "iter-2",
        previous_result_id: "result-1",
        current_result_id: "result-1",
        change_summary: "",
        rationale_shift_summary: "",
        continuity_status: "changed",
        continuity_summary: "",
      },
      next_recommended_move: {
        title: "Recommended next move",
        summary: "Review the current version or switch to another cut.",
        recommended_action_id: "request_revision",
        recommended_action_label: "Request revision",
        owner_action_required: "review_latest_result",
        tone: "attention",
      },
      responsibility: {
        owner_action_required: "review_latest_result",
        expected_agent_role: "repairer",
      },
      iteration_workbench: {
        selected_iteration_id: "iter-2",
        latest_iteration_id: "iter-2",
        iterations: [
          {
            iteration_id: "iter-2",
            title: "Slow the opener",
            goal: "Slow the opener and make the title entrance more deliberate.",
            status: "active",
            resolution_state: "open",
            requested_action: "revise",
            result_summary: "Two visible candidate cuts are available.",
          },
        ],
      },
      iteration_detail: {
        title: "Iteration Detail",
        summary: "Inspect the selected iteration to review visible turns, runs, and results.",
        selected_iteration_id: "iter-2",
        resource_uri: "video-thread://thread-1/iterations/iter-2.json",
        turn_count: 1,
        run_count: 1,
        result_count: 2,
      },
      conversation: { turns: [] },
      history: { cards: [] },
      production_journal: {
        title: "Production Journal",
        summary: "",
        entries: [
          {
            entry_id: "journal-result-1",
            entry_kind: "result",
            title: "Older result revisited",
            summary: "Earlier cut with a sharper title entrance.",
            stage: "result",
            status: "ready",
            iteration_id: "iter-2",
            task_id: "task-1",
            run_id: null,
            result_id: "result-1",
            actor_display_name: "Repairer",
            actor_role: "repairer",
            resource_refs: ["video-task://task-1/artifacts/final.mp4"],
          },
        ],
      },
      discussion_groups: { groups: [] },
      discussion_runtime: {
        title: "Discussion Runtime",
        summary: "Discuss the currently selected cut.",
        active_iteration_id: "iter-2",
        active_discussion_group_id: null,
        continuity_scope: "iteration",
        reply_policy: "continue_thread",
        default_intent_type: "discuss",
        default_reply_to_turn_id: "turn-1",
        default_related_result_id: "result-1",
        addressed_participant_id: "repairer-1",
        addressed_agent_id: "repairer-1",
        addressed_display_name: "Repairer",
        suggested_follow_up_modes: [],
        active_thread_title: "Version review",
        active_thread_summary: "Choose the cut you want to carry forward.",
        latest_owner_turn_id: "turn-1",
        latest_agent_turn_id: null,
        latest_agent_summary: "",
      },
      participant_runtime: {
        title: "Participant Runtime",
        summary: "",
        active_iteration_id: "iter-2",
        expected_participant_id: "repairer-1",
        expected_agent_id: "repairer-1",
        expected_display_name: "Repairer",
        expected_role: "repairer",
        continuity_mode: "keep_current_participant",
        follow_up_target_locked: true,
        recent_contributors: [],
      },
      process: {
        runs: [
          {
            run_id: "run-2",
            iteration_id: "iter-2",
            task_id: "task-1",
            role: "repairer",
            status: "completed",
            phase: "completed",
            output_summary: "Produced two candidate cuts.",
          },
        ],
      },
      participants: {
        items: [
          {
            participant_id: "owner",
            participant_type: "owner",
            role: "owner",
            display_name: "Owner",
          },
        ],
        management: {
          can_manage: true,
          can_invite: true,
          can_remove: true,
          invite_label: "Invite participant",
          invite_placeholder: "Agent id",
          default_role: "reviewer",
          default_capabilities: ["review_bundle:read"],
          remove_label: "Remove participant",
          removable_participant_ids: [],
          disabled_reason: "",
          context_hint: "Invite reviewers or helper agents into this thread.",
        },
      },
      actions: {
        items: [
          {
            action_id: "request_revision",
            label: "Request revision",
            description: "Create the next revision from the selected result and current goal.",
            tone: "strong",
            disabled: false,
          },
        ],
      },
      composer: {
        placeholder: "Ask why this version was made or request the next change.",
        submit_label: "Send",
        disabled: false,
        context_hint: "The selected cut is ready for review or a focused revision request.",
        target: {
          iteration_id: "iter-2",
          result_id: "result-1",
          addressed_participant_id: "repairer-1",
          addressed_agent_id: "repairer-1",
          addressed_display_name: "Repairer",
          agent_role: "repairer",
          agent_display_name: "Repairer",
          summary:
            "New messages will attach to iter-2, stay anchored to result-1, and hand off to Repairer.",
        },
      },
      render_contract: {
        default_focus_panel: "composer",
        panel_tone: "attention",
        display_priority: "normal",
        badge_order: ["owner_action_required"],
        panel_order: ["composer", "iteration_detail"],
        default_expanded_panels: ["composer", "iteration_detail"],
        sticky_primary_action_id: "request_revision",
        sticky_primary_action_emphasis: "strong",
        panel_presentations: [
          {
            panel_id: "iteration_detail",
            tone: "neutral",
            emphasis: "supporting",
            default_open: true,
            collapsible: true,
          },
        ],
      },
    },
  ];

  const iter2Details = [
    {
      thread_id: "thread-1",
      iteration_id: "iter-2",
      title: "Iteration Detail",
      summary: "This revision currently exposes two visible candidate cuts.",
      execution_summary: {
        title: "Execution Summary",
        summary: "Repairer produced task-2 while task-1 remains available for comparison.",
        task_id: "task-2",
        run_id: "thread-run:task-2",
        status: "completed",
        phase: "completed",
        agent_id: "repairer-1",
        agent_display_name: "Repairer",
        agent_role: "repairer",
        result_id: "result-2",
        discussion_group_id: null,
        reply_to_turn_id: "turn-1",
        latest_owner_turn_id: "turn-1",
        latest_agent_turn_id: null,
        is_active: true,
      },
      composer_target: {
        iteration_id: "iter-2",
        result_id: "result-2",
        addressed_participant_id: "repairer-1",
        addressed_agent_id: "repairer-1",
        addressed_display_name: "Repairer",
        agent_role: "repairer",
        agent_display_name: "Repairer",
        summary:
          "New messages will attach to iter-2, stay anchored to result-2, and hand off to Repairer.",
      },
      iteration: {
        iteration_id: "iter-2",
        thread_id: "thread-1",
        goal: "Slow the opener and make the title entrance more deliberate.",
        requested_action: "revise",
        preserve_working_parts: true,
        status: "active",
        resolution_state: "open",
        selected_result_id: "result-2",
        source_result_id: "result-1",
        responsible_role: "repairer",
        responsible_agent_id: "repairer-1",
      },
      turns: [],
      runs: [
        {
          run_id: "run-2",
          agent_id: "repairer-1",
          agent_display_name: "Repairer",
          role: "repairer",
          status: "completed",
          phase: "completed",
          output_summary: "Produced two candidate cuts.",
          task_id: "task-2",
        },
      ],
      results: [
        {
          result_id: "result-1",
          status: "ready",
          result_summary: "Earlier cut with a sharper title entrance.",
          selected: false,
          video_resource: "video-task://task-1/artifacts/final.mp4",
        },
        {
          result_id: "result-2",
          status: "ready",
          result_summary: "Selected cut with a slower title entrance.",
          selected: true,
          video_resource: "video-task://task-2/artifacts/final.mp4",
        },
      ],
    },
    {
      thread_id: "thread-1",
      iteration_id: "iter-2",
      title: "Iteration Detail",
      summary: "This revision currently exposes two visible candidate cuts.",
      execution_summary: {
        title: "Execution Summary",
        summary: "Repairer produced task-1 while task-2 remains available for comparison.",
        task_id: "task-1",
        run_id: "thread-run:task-1",
        status: "completed",
        phase: "completed",
        agent_id: "repairer-1",
        agent_display_name: "Repairer",
        agent_role: "repairer",
        result_id: "result-1",
        discussion_group_id: null,
        reply_to_turn_id: "turn-1",
        latest_owner_turn_id: "turn-1",
        latest_agent_turn_id: null,
        is_active: true,
      },
      composer_target: {
        iteration_id: "iter-2",
        result_id: "result-1",
        addressed_participant_id: "repairer-1",
        addressed_agent_id: "repairer-1",
        addressed_display_name: "Repairer",
        agent_role: "repairer",
        agent_display_name: "Repairer",
        summary:
          "New messages will attach to iter-2, stay anchored to result-1, and hand off to Repairer.",
      },
      iteration: {
        iteration_id: "iter-2",
        thread_id: "thread-1",
        goal: "Slow the opener and make the title entrance more deliberate.",
        requested_action: "revise",
        preserve_working_parts: true,
        status: "active",
        resolution_state: "open",
        selected_result_id: "result-1",
        source_result_id: "result-1",
        responsible_role: "repairer",
        responsible_agent_id: "repairer-1",
      },
      turns: [],
      runs: [
        {
          run_id: "run-1",
          agent_id: "repairer-1",
          agent_display_name: "Repairer",
          role: "repairer",
          status: "completed",
          phase: "completed",
          output_summary: "Produced two candidate cuts.",
          task_id: "task-1",
        },
      ],
      results: [
        {
          result_id: "result-1",
          status: "ready",
          result_summary: "Earlier cut with a sharper title entrance.",
          selected: true,
          video_resource: "video-task://task-1/artifacts/final.mp4",
        },
        {
          result_id: "result-2",
          status: "ready",
          result_summary: "Selected cut with a slower title entrance.",
          selected: false,
          video_resource: "video-task://task-2/artifacts/final.mp4",
        },
      ],
    },
  ];

  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requests.push({
      path,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });

    if (
      path === "/api/video-threads/thread-1/surface" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = surfaces[Math.min(surfaceIndex, surfaces.length - 1)];
      surfaceIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-2" &&
      (!init?.method || init.method === "GET")
    ) {
      const payload = iter2Details[Math.min(iter2DetailIndex, iter2Details.length - 1)];
      iter2DetailIndex += 1;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (
      path === "/api/video-threads/thread-1/iterations/iter-2/select-result" &&
      init?.method === "POST"
    ) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (path === "/api/tasks/task-1/result" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "completed",
          ready: true,
          summary: "Earlier cut with a sharper title entrance.",
          video_download_url: "/api/tasks/task-1/artifacts/final_video.mp4",
          script_download_url: "/api/tasks/task-1/artifacts/current_script.py",
          validation_report_download_url:
            "/api/tasks/task-1/artifacts/validations/validation_report_v1.json",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    if (path === "/api/tasks/task-2/result" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          task_id: "task-2",
          status: "completed",
          ready: true,
          summary: "Selected cut with a slower title entrance.",
          video_download_url: "/api/tasks/task-2/artifacts/final_video.mp4",
          script_download_url: "/api/tasks/task-2/artifacts/current_script.py",
          validation_report_download_url:
            "/api/tasks/task-2/artifacts/validations/validation_report_v1.json",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    return new Response("not found", { status: 404 });
  }) as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/threads/thread-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/threads/:threadId" element={<VideoThreadPage />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByText("Selected result: result-2")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Download video" })).toHaveAttribute(
    "href",
    "/api/tasks/task-2/artifacts/final_video.mp4"
  );
  const versions = screen.getByRole("region", { name: "Versions" });
  expect(within(versions).getByRole("heading", { name: "Versions" })).toBeInTheDocument();
  expect(
    within(versions).getAllByText("Earlier cut with a sharper title entrance.").length
  ).toBeGreaterThan(0);
  expect(
    within(versions).getByRole("link", { name: "Open task detail for result-1" })
  ).toHaveAttribute("href", "/tasks/task-1");
  expect(
    within(versions).getByRole("link", { name: "Download video for result-1" })
  ).toHaveAttribute("href", "/api/tasks/task-1/artifacts/final_video.mp4");
  expect(
    within(versions).getByRole("button", { name: "Set as current version result-1" })
  ).toBeInTheDocument();

  await user.click(
    within(versions).getByRole("button", { name: "Set as current version result-1" })
  );

  await waitFor(() => {
    expect(
      requests.some(
        (request) =>
          request.method === "POST" &&
          request.path === "/api/video-threads/thread-1/iterations/iter-2/select-result" &&
          request.body?.includes('"result_id":"result-1"')
      )
    ).toBe(true);
  });

  await waitFor(() => {
    expect(screen.getByText("Selected result: result-1")).toBeInTheDocument();
  });
  expect(screen.getByRole("link", { name: "Download video" })).toHaveAttribute(
    "href",
    "/api/tasks/task-1/artifacts/final_video.mp4"
  );
});
