import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { TasksPage } from "./TasksPage";

test("lists tasks and allows creating a task", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();

  const tasks: Array<{ task_id: string; status: string; display_title: string; title_source: string }> = [
    {
      task_id: "task-0",
      status: "completed",
      display_title: "蓝色圆形开场动画",
      title_source: "prompt"
    }
  ];

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/tasks" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: tasks }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    }
    if (path === "/api/tasks" && init?.method === "POST") {
      tasks.unshift({
        task_id: "task-1",
        status: "queued",
        display_title: "绿色叶片过渡动画",
        title_source: "prompt"
      });
      return new Response(
        JSON.stringify({ task_id: "task-1", display_title: "绿色叶片过渡动画", title_source: "prompt" }),
        {
          status: 200,
          headers: { "content-type": "application/json" }
        }
      );
    }
    if (path === "/api/videos/recent") {
      return new Response(
        JSON.stringify({
          items: [
            {
              task_id: "task-0",
              display_title: "蓝色圆形开场动画",
              title_source: "prompt",
              status: "completed",
              updated_at: "2026-03-26T08:00:00+00:00",
              latest_summary: "蓝色圆形已经顺利生成",
              latest_video_url: "/api/tasks/task-0/artifacts/final_video.mp4",
              latest_preview_url: "/api/tasks/task-0/artifacts/previews/frame.png"
            }
          ],
          next_cursor: null
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" }
        }
      );
    }
    if (path === "/api/tasks/task-0/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-0",
          status: "completed",
          ready: true,
          summary: "蓝色圆形已经顺利生成",
          video_download_url: "/api/tasks/task-0/artifacts/final_video.mp4",
          preview_download_urls: ["/api/tasks/task-0/artifacts/previews/frame.png"]
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" }
        }
      );
    }
    if (path === "/api/tasks/task-1/result") {
      return new Response(
        JSON.stringify({
          task_id: "task-1",
          status: "queued",
          ready: false,
          summary: null,
          video_download_url: null,
          preview_download_urls: []
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" }
        }
      );
    }
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/tasks"]}>
      <Routes>
        <Route path="/tasks" element={<TasksPage />} />
      </Routes>
    </MemoryRouter>
  );

  expect((await screen.findAllByText("蓝色圆形开场动画")).length).toBeGreaterThanOrEqual(2);
  expect(screen.getAllByText(/task-0/i).length).toBeGreaterThanOrEqual(2);

  await user.type(screen.getByLabelText(/任务描述/i), "画一个圆形");
  await user.click(screen.getByRole("button", { name: /创建任务/i }));

  expect((await screen.findAllByText("绿色叶片过渡动画")).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/task-1/i)).toBeInTheDocument();
});
