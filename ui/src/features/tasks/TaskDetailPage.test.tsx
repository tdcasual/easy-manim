import { render, screen } from "@testing-library/react";
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
          video_resource: "video-task://task-1/artifacts/final_video.mp4"
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

  expect(screen.getByText(/loading/i)).toBeInTheDocument();

  expect(await screen.findByText(/status/i)).toBeInTheDocument();
  expect(screen.getAllByText(/completed/i).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/validation passed/i)).toBeInTheDocument();
  expect(screen.getByText(/final_video\.mp4/i)).toBeInTheDocument();
});
