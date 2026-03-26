import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { TaskDetailPage } from "./TaskDetailPage";

test("shows task status and result summary", async () => {
  writeSessionToken("sess-token-1");
  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-1") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "Validation passed" },
          artifact_summary: {}
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "completed",
          ready: true,
          summary: "Validation passed",
          video_resource: "video-task://task-1/artifacts/final_video.mp4",
          video_download_url: "/api/tasks/task-1/artifacts/final_video.mp4",
          preview_download_urls: ["/api/tasks/task-1/artifacts/previews/frame-1.png"]
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-1"]}>
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(screen.getByText(/正在加载/i)).toBeInTheDocument();

  expect(await screen.findByText("task-1")).toBeInTheDocument();
  expect(screen.getAllByText(/已完成/i).length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText(/validation passed/i).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/final_video\.mp4/i)).toBeInTheDocument();
});

test("allows revising a task with feedback", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-1") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "completed",
          phase: "completed",
          attempt_count: 1,
          latest_validation_summary: { summary: "Validation passed" },
          artifact_summary: {}
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "completed",
          ready: true,
          summary: "Validation passed",
          video_resource: "video-task://task-1/artifacts/final_video.mp4",
          video_download_url: "/api/tasks/task-1/artifacts/final_video.mp4"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/revise" && init?.method === "POST") {
      return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } });
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-1"]}>
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByText("task-1")).toBeInTheDocument();

  await user.type(screen.getByLabelText(/修订说明/i), "改成蓝色");
  await user.click(screen.getByRole("button", { name: /提交修订/i }));

  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("/api/tasks/task-1/revise"))).toBe(true);
  });
});

test("allows retrying a failed task", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-1") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "failed",
          phase: "failed",
          attempt_count: 2,
          latest_validation_summary: { summary: "Validation failed" },
          artifact_summary: {}
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "failed",
          ready: true,
          summary: "Validation failed",
          video_resource: null,
          video_download_url: null
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/retry" && init?.method === "POST") {
      return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } });
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-1"]}>
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByText("task-1")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /失败重试/i }));

  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("/api/tasks/task-1/retry"))).toBe(true);
  });
});

test("allows cancelling an active task", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks/task-1") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "running",
          phase: "rendering",
          attempt_count: 1,
          latest_validation_summary: { summary: "" },
          artifact_summary: {}
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
          video_download_url: null
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }
    if (path === "/api/tasks/task-1/cancel" && init?.method === "POST") {
      return new Response(JSON.stringify({ task_id: "task-1", status: "cancelled" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks/task-1"]}>
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByText("task-1")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /取消任务/i }));

  await waitFor(() => {
    expect(calls.some((call) => call.url.includes("/api/tasks/task-1/cancel"))).toBe(true);
  });
});
