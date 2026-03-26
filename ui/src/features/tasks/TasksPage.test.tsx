import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { writeSessionToken } from "../../lib/session";
import { TasksPage } from "./TasksPage";

test("lists tasks and allows creating a task", async () => {
  writeSessionToken("sess-token-1");
  const user = userEvent.setup();

  const tasks: Array<{ task_id: string; status: string }> = [{ task_id: "task-0", status: "completed" }];

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
      tasks.unshift({ task_id: "task-1", status: "queued" });
      return new Response(JSON.stringify({ task_id: "task-1" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
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

  expect(await screen.findByText("task-0")).toBeInTheDocument();

  await user.type(screen.getByLabelText(/任务描述/i), "画一个圆形");
  await user.click(screen.getByRole("button", { name: /创建任务/i }));

  expect(await screen.findByText("task-1")).toBeInTheDocument();
});
