import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test } from "vitest";

import { writeLocale } from "../../app/locale";
import { ToastProvider } from "../../components/Toast";
import { writeSessionToken } from "../../lib/session";
import { VideosPageV2 } from "./VideosPageV2";

beforeEach(() => {
  writeSessionToken("sess-token-1");
  writeLocale("en-US");

  // @ts-expect-error - test shim
  globalThis.fetch = async (url: string, init?: RequestInit) => {
    const parsed = new URL(String(url), "http://example.test");
    const path = `${parsed.pathname}${parsed.search}`;

    if (path.startsWith("/api/videos/recent") && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              task_id: "task-target-001",
              display_title: "Ocean waves",
              status: "completed",
              updated_at: "2026-03-28T00:00:00Z",
              latest_preview_url: null,
              latest_video_url: null,
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    return new Response("not found", { status: 404 });
  };
});

test("videos search matches task ids as well as titles", async () => {
  const user = userEvent.setup();

  render(
    <MemoryRouter>
      <ToastProvider>
        <VideosPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByText("Ocean waves")).toBeInTheDocument();

  await user.type(screen.getByPlaceholderText(/search video title or task id/i), "task-target-001");

  await waitFor(() => {
    expect(screen.getByText("Ocean waves")).toBeInTheDocument();
  });
});

test("videos filter controls follow the active locale", async () => {
  const user = userEvent.setup();

  render(
    <MemoryRouter>
      <ToastProvider>
        <VideosPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  await screen.findByText("Ocean waves");

  await user.type(screen.getByPlaceholderText(/search video title or task id/i), "ocean");
  expect(screen.getByRole("button", { name: /clear search/i })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /filter/i }));

  expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /completed/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /in progress/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /queued/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /failed/i })).toBeInTheDocument();
});
