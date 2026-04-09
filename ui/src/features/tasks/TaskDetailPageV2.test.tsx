import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { ToastProvider } from "../../components/Toast";
import { writeSessionToken } from "../../lib/session";
import { TaskDetailPageV2 } from "./TaskDetailPageV2";

test("renders translated task status and phase labels", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-1") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          display_title: "蓝色圆形开场动画",
          title_source: "prompt",
          status: "running",
          phase: "rendering",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "running",
          ready: false,
          summary: null,
          video_resource: null,
          video_download_url: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-1"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "蓝色圆形开场动画" })).toBeInTheDocument();
  expect(screen.getAllByText("执行中").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("渲染中").length).toBeGreaterThanOrEqual(1);
});

test("task detail promotes the thread workspace as the canonical collaboration page", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-threaded") {
      return new Response(
        JSON.stringify({
          task_id: "task-threaded",
          thread_id: "thread-42",
          display_title: "Threaded video",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-threaded/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-threaded",
          status: "completed",
          ready: true,
          summary: "done",
          video_resource: null,
          video_download_url: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-threaded"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Threaded video" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /thread workspace/i })).toBeInTheDocument();
  expect(
    screen.getByText(
      /open the canonical video page for discussion, versions, and revision history/i
    )
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /open thread workspace/i })).toHaveAttribute(
    "href",
    "/threads/thread-42"
  );
  expect(screen.queryByText(/video collaboration workbench/i)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/discussion/i)).not.toBeInTheDocument();
});

test("shows an error alert when task detail loading fails", async () => {
  writeSessionToken("sess-token-1");

  globalThis.fetch = vi.fn(async () => new Response("boom", { status: 500 }));

  render(
    <MemoryRouter initialEntries={["/tasks/task-404"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(/加载失败/i);
});

test("task detail resolves relative preview posters for the video player", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-2") {
      return new Response(
        JSON.stringify({
          task_id: "task-2",
          display_title: "相对路径 poster 测试",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-2/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-2",
          status: "completed",
          ready: true,
          summary: "done",
          video_resource: null,
          video_download_url: "artifacts/videos/final.mp4",
          preview_download_urls: ["artifacts/previews/frame_001.png"],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  const { container } = render(
    <MemoryRouter initialEntries={["/tasks/task-2"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "相对路径 poster 测试" })).toBeInTheDocument();
  const video = container.querySelector("video.main-video-player");
  expect(video).not.toBeNull();
  expect(video).toHaveAttribute("poster", "/artifacts/previews/frame_001.png");
});

test("task detail shows guaranteed delivery banner when output is degraded fallback", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-3") {
      return new Response(
        JSON.stringify({
          task_id: "task-3",
          display_title: "保底交付测试",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 3,
          delivery_status: "delivered",
          resolved_task_id: "task-3-child",
          completion_mode: "degraded",
          delivery_tier: "guided_generate",
          delivery_stop_reason: null,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-3/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-3",
          status: "completed",
          ready: true,
          delivery_status: "delivered",
          completion_mode: "degraded",
          delivery_tier: "guided_generate",
          resolved_task_id: "task-3-child",
          delivery_stop_reason: null,
          summary: "degraded delivery",
          video_resource: null,
          video_download_url: "artifacts/videos/final.mp4",
          preview_download_urls: ["artifacts/previews/frame_001.png"],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-3"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "保底交付测试" })).toBeInTheDocument();
  expect(screen.getByText(/保底出片|简化交付/)).toBeInTheDocument();
});

test("task detail hides manual retry while guaranteed delivery is still pending", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-4") {
      return new Response(
        JSON.stringify({
          task_id: "task-4",
          display_title: "保底处理中",
          title_source: "prompt",
          status: "failed",
          phase: "failed",
          attempt_count: 1,
          delivery_status: "pending",
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-4/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-4",
          status: "failed",
          ready: false,
          delivery_status: "pending",
          summary: null,
          video_resource: null,
          video_download_url: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-4"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "保底处理中" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /重试|retry/i })).not.toBeInTheDocument();
});

test("task detail renders owner review panel and submits the recommended workflow action", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;

    if (path === "/api/tasks/task-5") {
      return new Response(
        JSON.stringify({
          task_id: "task-5",
          display_title: "工作流评审面板测试",
          title_source: "prompt",
          status: "failed",
          phase: "failed",
          attempt_count: 2,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-5/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-5",
          status: "failed",
          ready: false,
          summary: "needs another pass",
          video_resource: null,
          video_download_url: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-5/review-bundle" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          task_id: "task-5",
          status: "failed",
          phase: "failed",
          workflow_review_controls: {
            panel_header: {
              title: "Workflow review controls",
              tone: "attention",
              summary: "Pin suggested workflow memory before creating the next revision.",
              badges: [
                {
                  badge_id: "recommended_action",
                  label: "Recommended",
                  value: "pin_and_revise",
                  tone: "attention",
                },
                {
                  badge_id: "acceptance_blockers",
                  label: "Blockers",
                  value: "1",
                  tone: "blocked",
                },
              ],
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
                      summary:
                        "Attach the most relevant shared workflow memory before creating the next revision.",
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
                      payload: {
                        review_decision: {
                          decision: "revise",
                          summary: "Pin recommended workflow memory before revising",
                          feedback: "Use the refreshed workflow memory in the next revision.",
                        },
                        pin_workflow_memory_ids: ["mem-a"],
                      },
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
              badge_order: ["recommended_action", "acceptance_blockers"],
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
    }
    if (path === "/api/tasks/task-5/review-decision" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          task_id: "task-5",
          action: "revise",
          created_task_id: "task-5-child",
          reason: "revision_created",
          refresh_scope: "navigate",
          refresh_task_id: "task-5-child",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-5-child") {
      return new Response(
        JSON.stringify({
          task_id: "task-5-child",
          display_title: "工作流评审面板测试 - 子任务",
          title_source: "prompt",
          status: "queued",
          phase: "queued",
          attempt_count: 0,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-5-child/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-5-child",
          status: "queued",
          ready: false,
          summary: null,
          video_resource: null,
          video_download_url: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-5-child/review-bundle") {
      return new Response(
        JSON.stringify({
          task_id: "task-5-child",
          status: "queued",
          phase: "queued",
          workflow_review_controls: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  globalThis.fetch = fetchMock as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/tasks/task-5"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "工作流评审面板测试" })).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: /workflow review controls/i })
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Pin suggested workflow memory before creating the next revision/i)
  ).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: /pin memory and revise/i })).toHaveLength(1);

  await user.click(screen.getByRole("button", { name: /pin memory and revise/i }));

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/tasks/task-5/review-decision"),
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  const reviewDecisionCall = fetchMock.mock.calls.find(
    ([url, init]) =>
      String(url).includes("/api/tasks/task-5/review-decision") && init?.method === "POST"
  );
  expect(reviewDecisionCall).toBeDefined();
  expect(JSON.parse(String(reviewDecisionCall?.[1]?.body))).toMatchObject({
    review_decision: {
      decision: "revise",
      summary: "Pin recommended workflow memory before revising",
    },
    pin_workflow_memory_ids: ["mem-a"],
  });
  expect(await screen.findByText(/工作流动作已执行/i, {}, { timeout: 3000 })).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "工作流评审面板测试 - 子任务" })
  ).toBeInTheDocument();
});

test("task detail refreshes review panel feedback after a panel-only workflow action", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  let reviewBundleRequestCount = 0;
  let taskRequestCount = 0;
  let resultRequestCount = 0;

  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;

    if (path === "/api/tasks/task-6") {
      taskRequestCount += 1;
      return new Response(
        JSON.stringify({
          task_id: "task-6",
          display_title: "工作流面板局部刷新测试",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-6/result") {
      resultRequestCount += 1;
      return new Response(
        JSON.stringify({
          task_id: "task-6",
          status: "completed",
          ready: true,
          summary: "ready to accept",
          video_resource: null,
          video_download_url: "artifacts/videos/final.mp4",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-6/review-bundle" && (!init?.method || init.method === "GET")) {
      reviewBundleRequestCount += 1;
      return new Response(
        JSON.stringify({
          task_id: "task-6",
          status: "completed",
          phase: "completed",
          workflow_review_controls: {
            panel_header: {
              title: "Workflow review controls",
              tone: "attention",
              summary: "Keep the review open while the workflow stays under inspection.",
              badges: [
                {
                  badge_id: "recommended_action",
                  label: "Recommended",
                  value: "keep_reviewing",
                  tone: "attention",
                },
              ],
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
                      action_id: "keep_reviewing",
                      title: "Keep reviewing",
                      button_label: "Keep reviewing",
                      action_family: "review_decision",
                      summary:
                        "Acknowledge the latest workflow step without reloading the task shell.",
                      blocked: false,
                      reasons: [],
                      is_primary: true,
                      intent: {
                        review_decision: "escalate",
                        mutates_workflow_memory: false,
                        workflow_memory_change: null,
                      },
                      payload: {
                        review_decision: {
                          decision: "escalate",
                          summary: "Keep the review open",
                        },
                      },
                    },
                  ],
                },
              ],
            },
            status_summary: {
              recommended_action_id: "keep_reviewing",
              acceptance_ready: false,
              acceptance_blockers: ["needs_follow_up"],
              pinned_memory_count: 1,
              pending_memory_recommendation_count: 0,
              has_pending_memory_updates: false,
              latest_workflow_memory_event_type: null,
              latest_workflow_memory_event_at: null,
            },
            applied_action_feedback:
              reviewBundleRequestCount > 1
                ? {
                    event_type: "review_kept_open",
                    tone: "success",
                    title: "Review kept open",
                    summary: "The panel refreshed in place after the workflow action completed.",
                    memory_id: null,
                    created_at: "2026-03-31T08:40:00Z",
                    follow_up_action_id: null,
                  }
                : null,
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
              sticky_primary_action_id: "keep_reviewing",
              sticky_primary_action_emphasis: "strong",
              applied_feedback_dismissible: false,
            },
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-6/review-decision" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          task_id: "task-6",
          action: "escalate",
          created_task_id: null,
          reason: "workflow_budget_exhausted",
          refresh_scope: "panel_only",
          refresh_task_id: "task-6",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  globalThis.fetch = fetchMock as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/tasks/task-6"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(
    await screen.findByRole("heading", { name: "工作流面板局部刷新测试" })
  ).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /keep reviewing/i })).toBeInTheDocument();
  expect(screen.queryByText(/review kept open/i)).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /keep reviewing/i }));

  expect(await screen.findByText(/工作流动作已执行/i, {}, { timeout: 3000 })).toBeInTheDocument();
  expect(await screen.findByText(/review kept open/i)).toBeInTheDocument();
  expect(
    screen.getByText(/the panel refreshed in place after the workflow action completed/i)
  ).toBeInTheDocument();
  expect(taskRequestCount).toBe(1);
  expect(resultRequestCount).toBe(1);
  expect(reviewBundleRequestCount).toBe(2);
});

test("task detail reloads task state after a task-and-panel workflow action", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  let reviewBundleRequestCount = 0;
  let taskRequestCount = 0;
  let resultRequestCount = 0;

  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;

    if (path === "/api/tasks/task-7") {
      taskRequestCount += 1;
      return new Response(
        JSON.stringify({
          task_id: "task-7",
          display_title: "工作流整页刷新测试",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          delivery_status: "delivered",
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-7/result") {
      resultRequestCount += 1;
      return new Response(
        JSON.stringify({
          task_id: "task-7",
          status: "completed",
          ready: true,
          summary:
            resultRequestCount > 1
              ? "accepted result is now reflected in the task shell"
              : "ready to accept",
          video_resource: null,
          video_download_url: "artifacts/videos/final.mp4",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-7/review-bundle" && (!init?.method || init.method === "GET")) {
      reviewBundleRequestCount += 1;
      return new Response(
        JSON.stringify({
          task_id: "task-7",
          status: "completed",
          phase: "completed",
          workflow_review_controls: {
            panel_header: {
              title: "Workflow review controls",
              tone: "ready",
              summary: "Accept the best version when it meets the workflow bar.",
              badges: [
                {
                  badge_id: "recommended_action",
                  label: "Recommended",
                  value: "accept_best_version",
                  tone: "ready",
                },
              ],
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
                      action_id: "accept_best_version",
                      title: "Accept best version",
                      button_label: "Accept best version",
                      action_family: "review_decision",
                      summary: "Promote the current best result without creating a new child task.",
                      blocked: false,
                      reasons: [],
                      is_primary: true,
                      intent: {
                        review_decision: "accept",
                        mutates_workflow_memory: false,
                        workflow_memory_change: null,
                      },
                      payload: {
                        review_decision: {
                          decision: "accept",
                          summary: "Accept the current best version",
                        },
                      },
                    },
                  ],
                },
              ],
            },
            status_summary: {
              recommended_action_id: "accept_best_version",
              acceptance_ready: true,
              acceptance_blockers: [],
              pinned_memory_count: 0,
              pending_memory_recommendation_count: 0,
              has_pending_memory_updates: false,
              latest_workflow_memory_event_type: null,
              latest_workflow_memory_event_at: null,
            },
            applied_action_feedback: null,
            render_contract: {
              badge_order: ["recommended_action"],
              panel_tone: "ready",
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
              sticky_primary_action_id: "accept_best_version",
              sticky_primary_action_emphasis: "strong",
              applied_feedback_dismissible: false,
            },
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-7/review-decision" && init?.method === "POST") {
      return new Response(
        JSON.stringify({
          task_id: "task-7",
          action: "accept",
          created_task_id: null,
          reason: "winner_selected",
          refresh_scope: "task_and_panel",
          refresh_task_id: "task-7",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  globalThis.fetch = fetchMock as typeof fetch;

  render(
    <MemoryRouter initialEntries={["/tasks/task-7"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "工作流整页刷新测试" })).toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: /accept best version/i }));

  expect(await screen.findByText(/工作流动作已执行/i, {}, { timeout: 3000 })).toBeInTheDocument();
  expect(
    await screen.findByText(/accepted result is now reflected in the task shell/i)
  ).toBeInTheDocument();
  expect(taskRequestCount).toBe(2);
  expect(resultRequestCount).toBe(2);
  expect(reviewBundleRequestCount).toBe(2);
});

test("task detail without thread id does not request legacy discussion transport", async () => {
  writeSessionToken("sess-token-1");
  const requestedPaths: string[] = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requestedPaths.push(`${init?.method ?? "GET"} ${path}`);

    if (path === "/api/tasks/task-8") {
      return new Response(
        JSON.stringify({
          task_id: "task-8",
          display_title: "Legacy-free task detail",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-8/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-8",
          status: "completed",
          ready: true,
          summary: "ready",
          video_resource: null,
          video_download_url: "artifacts/videos/final.mp4",
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-8/review-bundle") {
      return new Response(
        JSON.stringify({
          task_id: "task-8",
          status: "completed",
          phase: "completed",
          workflow_review_controls: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-8"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(
    await screen.findByRole("heading", { name: "Legacy-free task detail" })
  ).toBeInTheDocument();
  expect(screen.queryByText(/video discussion & process/i)).not.toBeInTheDocument();
  expect(screen.queryByRole("textbox", { name: /discuss this video/i })).not.toBeInTheDocument();
  expect(
    requestedPaths.some(
      (entry) => entry.includes("/discussion-thread") || entry.includes("/discussion-messages")
    )
  ).toBe(false);
});

test("task detail with thread id stays on the thread-native workbench path", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const requestedPaths: string[] = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    requestedPaths.push(`${init?.method ?? "GET"} ${path}`);

    if (path === "/api/tasks/task-9") {
      return new Response(
        JSON.stringify({
          task_id: "task-9",
          thread_id: "thread-99",
          display_title: "Thread-native detail",
          title_source: "prompt",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {},
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-9/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-9",
          status: "completed",
          ready: true,
          summary: "ready",
          video_resource: null,
          video_download_url: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-9/review-bundle") {
      return new Response(
        JSON.stringify({
          task_id: "task-9",
          status: "completed",
          phase: "completed",
          workflow_review_controls: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-9"]}>
      <ToastProvider>
        <Routes>
          <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
          <Route path="/threads/:threadId" element={<div>Thread route placeholder</div>} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "Thread-native detail" })).toBeInTheDocument();
  const link = screen.getByRole("link", { name: /open thread workspace/i });
  expect(link).toHaveAttribute("href", "/threads/thread-99");
  await user.click(link);
  expect(await screen.findByText("Thread route placeholder")).toBeInTheDocument();
  expect(
    requestedPaths.some(
      (entry) => entry.includes("/discussion-thread") || entry.includes("/discussion-messages")
    )
  ).toBe(false);
});
