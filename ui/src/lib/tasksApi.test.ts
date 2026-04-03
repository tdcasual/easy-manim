import { afterEach, expect, test, vi } from "vitest";

import { getReviewBundle, getTaskResult } from "./tasksApi";

afterEach(() => {
  vi.restoreAllMocks();
});

test("getReviewBundle returns owner review controls with render contract", async () => {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), "http://example.test").pathname;
    expect(path).toBe("/api/tasks/task-1/review-bundle");

    return new Response(
      JSON.stringify({
        task_id: "task-1",
        status: "failed",
        phase: "failed",
        workflow_review_controls: {
          panel_header: {
            tone: "attention",
            summary: "Pin suggested workflow memory before creating the next revision.",
            badges: [],
            highlighted_event: null,
          },
          action_sections: {
            items: [
              {
                section_id: "recommended",
                title: "Recommended next step",
                summary: "The strongest next action based on the current workflow state.",
                items: [
                  {
                    action_id: "pin_and_revise",
                    title: "Pin suggested memory and revise",
                    button_label: "Pin memory and revise",
                    action_family: "combined",
                    summary: "Attach the most relevant shared workflow memory before creating the next revision.",
                    blocked: false,
                    reasons: [],
                    is_primary: true,
                    intent: {
                      review_decision: "revise",
                      mutates_workflow_memory: true,
                      workflow_memory_change: {
                        pin_memory_ids: ["mem-a"],
                        unpin_memory_ids: [],
                        pin_count: 1,
                        unpin_count: 0,
                      },
                    },
                    payload: {},
                  },
                ],
              },
            ],
          },
          status_summary: {
            recommended_action_id: "pin_and_revise",
            acceptance_ready: false,
            acceptance_blockers: ["task_not_completed"],
            pinned_memory_count: 0,
            pending_memory_recommendation_count: 1,
            has_pending_memory_updates: true,
            latest_workflow_memory_event_type: null,
            latest_workflow_memory_event_at: null,
          },
          applied_action_feedback: null,
          render_contract: {
            badge_order: ["recommended_action"],
            panel_tone: "attention",
            display_priority: "high",
            section_order: ["recommended"],
            default_focus_section_id: "recommended",
            default_expanded_section_ids: ["recommended"],
            section_presentations: [
              {
                section_id: "recommended",
                tone: "accent",
                collapsible: false,
              },
            ],
            sticky_primary_action_id: "pin_and_revise",
            sticky_primary_action_emphasis: "strong",
            applied_feedback_dismissible: false,
          },
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } }
    );
  }) as typeof fetch;

  const bundle = await getReviewBundle("task-1", "sess-token-1");

  expect(bundle.workflow_review_controls?.render_contract?.panel_tone).toBe("attention");
  expect(bundle.workflow_review_controls?.render_contract?.badge_order).toEqual(["recommended_action"]);
  expect(bundle.workflow_review_controls?.render_contract?.sticky_primary_action_id).toBe(
    bundle.workflow_review_controls?.status_summary?.recommended_action_id
  );
  expect(
    bundle.workflow_review_controls?.render_contract?.section_presentations[0]?.collapsible
  ).toBe(false);
  expect(bundle.workflow_review_controls?.action_sections?.items[0]?.items[0]?.action_id).toBe(
    "pin_and_revise"
  );
});

test("getReviewBundle no longer exposes the legacy task discussion surface", async () => {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), "http://example.test").pathname;
    expect(path).toBe("/api/tasks/task-legacy/review-bundle");

    return new Response(
      JSON.stringify({
        task_id: "task-legacy",
        status: "completed",
        phase: "completed",
        workflow_review_controls: null,
      }),
      { status: 200, headers: { "content-type": "application/json" } }
    );
  }) as typeof fetch;

  const bundle = await getReviewBundle("task-legacy", "sess-token-1");

  expect(bundle.task_id).toBe("task-legacy");
  expect("video_discussion_surface" in bundle).toBe(false);
});

test("getTaskResult exposes task artifact download urls", async () => {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), "http://example.test").pathname;
    expect(path).toBe("/api/tasks/task-2/result");

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
  }) as typeof fetch;

  const result = await getTaskResult("task-2", "sess-token-1");

  expect(result.video_download_url).toBe("/api/tasks/task-2/artifacts/final_video.mp4");
  expect(result.script_download_url).toBe("/api/tasks/task-2/artifacts/current_script.py");
  expect(result.validation_report_download_url).toBe(
    "/api/tasks/task-2/artifacts/validations/validation_report_v1.json"
  );
});
