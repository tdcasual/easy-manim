import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { App } from "../../app/App";
import { writeSessionToken } from "../../lib/session";

test("renders video navigation and recent video cards", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = vi.fn(async (url: string) => {
    const path = new URL(String(url), "http://example.test").pathname;
    if (path === "/api/videos/recent") {
      return new Response(
        JSON.stringify({
          items: [
            {
              task_id: "task-1",
              display_title: "蓝色圆形开场动画",
              title_source: "prompt",
              status: "completed",
              updated_at: "2026-03-26T08:00:00+00:00",
              latest_summary: "蓝色圆形已经顺利生成",
              latest_video_url: "/api/tasks/task-1/artifacts/final_video.mp4",
              latest_preview_url: "/api/tasks/task-1/artifacts/previews/frame.png"
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
    return new Response("not found", { status: 404 });
  });

  render(
    <MemoryRouter initialEntries={["/videos"]}>
      <App />
    </MemoryRouter>
  );

  expect(await screen.findByRole("link", { name: /视频/i })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /^视频$/i })).toBeInTheDocument();
  expect(screen.getByText("蓝色圆形开场动画")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /查看详情/i })).toBeInTheDocument();
});
