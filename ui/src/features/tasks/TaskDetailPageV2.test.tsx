import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

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
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "蓝色圆形开场动画" })).toBeInTheDocument();
  expect(screen.getAllByText("执行中").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("渲染中").length).toBeGreaterThanOrEqual(1);
});

test("shows an error alert when task detail loading fails", async () => {
  writeSessionToken("sess-token-1");

  globalThis.fetch = vi.fn(async () => new Response("boom", { status: 500 }));

  render(
    <MemoryRouter initialEntries={["/tasks/task-404"]}>
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
      </Routes>
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
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
      </Routes>
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
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
      </Routes>
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
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskDetailPageV2 />} />
      </Routes>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: "保底处理中" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /重试|retry/i })).not.toBeInTheDocument();
});
