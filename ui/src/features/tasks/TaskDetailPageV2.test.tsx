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
