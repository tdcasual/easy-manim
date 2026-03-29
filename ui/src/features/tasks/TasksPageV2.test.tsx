import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { ToastProvider } from "../../components/Toast";
import { writeLocale } from "../../app/locale";
import { clearSessionToken, writeSessionToken } from "../../lib/session";
import { TasksPageV2 } from "./TasksPageV2";

vi.mock("../../components/AnimatedContainer", () => ({
  AnimatedContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  HoverAnimation: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

test("tasks page renders localized placeholder and clean tab labels", async () => {
  writeSessionToken("sess-token-1");

  // @ts-expect-error - test shim
  globalThis.fetch = async (url: string, init?: RequestInit) => {
    const parsed = new URL(String(url), "http://example.test");
    const path = `${parsed.pathname}${parsed.search}`;

    if (path === "/api/tasks" && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              task_id: "task-geometry-intro",
              status: "running",
              display_title: "圆与切线的动态引入",
            },
          ],
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      );
    }

    if (path.startsWith("/api/videos/recent") && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              task_id: "task-sine-wave",
              display_title: "带中文标签的正弦波动画",
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

  const { container } = render(
    <MemoryRouter>
      <ToastProvider>
        <TasksPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  expect(
    await screen.findByPlaceholderText(/做一个简洁的蓝色圆形动画|生成一个带中文标题的柱状图视频/)
  ).toBeInTheDocument();
  expect(screen.queryByPlaceholderText("tasks.quickPlaceholder")).not.toBeInTheDocument();

  await waitFor(() => {
    const labels = Array.from(container.querySelectorAll(".tab-label")).map((node) =>
      node.textContent?.trim()
    );
    expect(labels).toEqual(["全部", "进行中", "已完成"]);
  });
});

test("shows an error state instead of an empty state when the first task load fails", async () => {
  writeSessionToken("sess-token-1");

  globalThis.fetch = vi.fn(async () => new Response("boom", { status: 500 }));

  render(
    <MemoryRouter>
      <ToastProvider>
        <TasksPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(/加载任务列表失败/i);
  expect(screen.queryByText(/还没有任务呢/i)).not.toBeInTheDocument();
});

test("quick prompt chips require auth instead of failing silently", async () => {
  const user = userEvent.setup();
  clearSessionToken();
  writeLocale("zh-CN");
  globalThis.fetch = vi.fn();

  render(
    <MemoryRouter>
      <ToastProvider>
        <TasksPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  await user.click(screen.getByPlaceholderText(/做一个简洁的蓝色圆形动画|生成一个带中文标题的柱状图视频/));
  await user.click(await screen.findByRole("button", { name: /画一个蓝色圆形/ }));

  expect(await screen.findByRole("dialog", { name: /登录/ })).toBeInTheDocument();
  expect(globalThis.fetch).not.toHaveBeenCalled();
});

test("quick prompt chips use the active locale", async () => {
  const user = userEvent.setup();
  clearSessionToken();
  writeLocale("en-US");
  globalThis.fetch = vi.fn();

  render(
    <MemoryRouter>
      <ToastProvider>
        <TasksPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  const input = await screen.findByPlaceholderText(/Animate a simple blue circle|Create a bar-chart video/);
  await user.click(input);

  expect(
    await screen.findByRole("button", {
      name: /Animate a clean blue circle/,
    })
  ).toBeInTheDocument();

  await act(async () => {
    writeLocale("zh-CN");
  });
});

test("tasks page chrome follows the active locale", async () => {
  writeSessionToken("sess-token-1");
  writeLocale("en-US");

  // @ts-expect-error - test shim
  globalThis.fetch = async (url: string, init?: RequestInit) => {
    const parsed = new URL(String(url), "http://example.test");
    const path = `${parsed.pathname}${parsed.search}`;

    if (path === "/api/tasks" && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    if (path.startsWith("/api/videos/recent") && (!init?.method || init.method === "GET")) {
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }

    return new Response("not found", { status: 404 });
  };

  const { container } = render(
    <MemoryRouter>
      <ToastProvider>
        <TasksPageV2 />
      </ToastProvider>
    </MemoryRouter>
  );

  expect(await screen.findByRole("heading", { name: /task workspace/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /refresh list/i })).toBeInTheDocument();
  expect(await screen.findByText(/no tasks yet/i)).toBeInTheDocument();

  await waitFor(() => {
    const labels = Array.from(container.querySelectorAll(".tab-label")).map((node) =>
      node.textContent?.trim()
    );
    expect(labels).toEqual(["All", "In progress", "Completed"]);
  });

  await act(async () => {
    writeLocale("zh-CN");
  });
});
