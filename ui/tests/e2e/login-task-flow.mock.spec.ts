import { test, expect } from "@playwright/test";

test("logs in, creates a task, and opens the task detail (mock api)", async ({ page }) => {
  const tasks: Array<{ task_id: string; status: string }> = [{ task_id: "task-0", status: "completed" }];

  await page.route("**/api/sessions", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_token: "sess-token-1",
        agent_id: "agent-a",
        name: "Agent A",
        expires_at: "2030-01-01T00:00:00Z"
      })
    });
  });

  await page.route("**/api/tasks", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: tasks }) });
    }
    if (method === "POST") {
      tasks.unshift({ task_id: "task-1", status: "queued" });
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ task_id: "task-1" }) });
    }
    return route.fallback();
  });

  await page.route("**/api/tasks/task-1", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "task-1",
        status: "completed",
        phase: "completed",
        attempt_count: 1,
        latest_validation_summary: { summary: "Validation passed" },
        artifact_summary: {}
      })
    });
  });

  await page.route("**/api/tasks/task-1/result", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: "task-1",
        status: "completed",
        ready: true,
        summary: "Validation passed",
        video_resource: "video-task://task-1/artifacts/final_video.mp4"
      })
    });
  });

  await page.goto("/login");
  await page.getByLabel("Agent token").fill("easy-manim.agent-a.secret");
  await page.getByRole("button", { name: /log in/i }).click();

  await expect(page.getByRole("heading", { name: /^tasks$/i })).toBeVisible();

  await expect(page.getByText("task-0")).toBeVisible();
  await page.getByLabel(/prompt/i).fill("draw a circle");
  await page.getByRole("button", { name: /create task/i }).click();
  await expect(page.getByText("task-1")).toBeVisible();

  await page.getByText("task-1").click();
  await expect(page.getByText("final_video.mp4")).toBeVisible();
});

